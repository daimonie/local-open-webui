FROM python:3.12.3

# Create a group and user
RUN groupadd -r python-role && useradd -m -r -g python-role pythonuser

# Create the project directory and set ownership
RUN mkdir -p /opt/container && chown -R pythonuser:python-role /opt/container

# Create the output directory and set permissions
RUN mkdir -p /opt/container/output && chown -R pythonuser:python-role /opt/container/output && chmod 755 /opt/container/output

# Switch to the non-root user
# USER pythonuser

# Set working directory
WORKDIR /opt/container

# Copy container directory into docker image
COPY --chown=pythonuser:python-role container/ .

# Install poetry using pip
RUN pip install poetry

# Add poetry to PATH
ENV PATH="/home/pythonuser/.local/bin:$PATH"

# Verify poetry installation
RUN poetry --version

# Install dependencies using Poetry
RUN poetry install
# Set the entrypoint to bash
ENTRYPOINT ["/bin/bash"]
