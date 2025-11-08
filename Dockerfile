FROM python:3.11-slim

# Install system dependencies + Node.js
RUN apt-get update && apt-get install -y \
    curl \
    git \
    bash \
    ca-certificates \
    gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py .
COPY claude_oauth_api_secure_multitenant.py .
COPY mcp_proxy.py .

# Create workspaces root with proper permissions
RUN mkdir -p /workspaces && chmod 755 /workspaces

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash appuser && \
    chown -R appuser:appuser /app /workspaces

# Switch to non-root user
USER appuser

# Install Claude CLI as appuser (will install to ~/.local/bin)
RUN bash -c "curl -fsSL https://claude.ai/install.sh | bash"

# Add Claude CLI to PATH
ENV PATH="/home/appuser/.local/bin:${PATH}"

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run application
CMD ["python", "server.py"]
