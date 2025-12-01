#!/bin/bash

# Blaxel Remote Sandbox Deployment Script
# This script configures and deploys a sandbox directly to Blaxel,
# triggering a remote cloud build to save local disk space.

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SANDBOX_NAME="manim-sandbox"
# Note: Port 8080 is reserved by Blaxel Sandbox API, we don't need to list it in blaxel.toml ports
# but we need to know the Sandbox is of type "sandbox"

# Helper functions
print_header() {
    echo -e "\n${BLUE}================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check Blaxel CLI
    if ! command -v bl &> /dev/null; then
        print_error "Blaxel CLI is not installed."
        echo -e "Install with: ${YELLOW}curl -fsSL https://raw.githubusercontent.com/blaxel-ai/toolkit/main/install.sh | sh${NC}"
        exit 1
    fi
    print_success "Blaxel CLI is installed"

    # Check if Dockerfile exists
    if [ ! -f "Dockerfile.sandbox" ]; then
        print_error "Dockerfile.sandbox not found in current directory"
        exit 1
    fi
    print_success "Dockerfile.sandbox found"

    # Check Blaxel authentication
    print_info "Checking Blaxel authentication..."
    if ! bl workspaces &> /dev/null; then
        print_warning "Not logged in to Blaxel"
        echo -e "Please login with: ${YELLOW}bl login${NC}"
        exit 1
    fi
    print_success "Authenticated with Blaxel"
}

create_config() {
    print_header "Generating Blaxel Configuration"

    # Blaxel needs a blaxel.toml to know how to build and deploy this as a sandbox
    # We create it dynamically to ensure it matches your requirements.
    
    if [ -f "blaxel.toml" ]; then
        print_warning "blaxel.toml already exists. Backing up to blaxel.toml.bak"
        mv blaxel.toml blaxel.toml.bak
    fi

    print_info "Creating blaxel.toml..."
    
    cat << EOF > blaxel.toml
name = "${SANDBOX_NAME}"
type = "sandbox"
description = "Custom Manim + FFmpeg Sandbox"

[runtime]
memory = 4096  # 4GB RAM should be sufficient for rendering

# Note: We do not explicitly list port 8080 here as it is injected by the sandbox-api
# If you run a custom server (like a flask app) on another port (e.g., 3000), add it here.
EOF

    print_success "blaxel.toml created"
    
    # Check if we need to rename Dockerfile.sandbox to Dockerfile
    # Blaxel deployment typically looks for standard "Dockerfile"
    if [ -f "Dockerfile.sandbox" ] && [ ! -f "Dockerfile" ]; then
        print_info "Linking Dockerfile.sandbox to Dockerfile for deployment..."
        cp Dockerfile.sandbox Dockerfile
    fi
}

deploy_to_blaxel() {
    print_header "Deploying to Blaxel (Remote Build)"

    print_info "Starting deployment..."
    print_info "This will upload your context and build the image on Blaxel's infrastructure."
    print_info "This may take a few minutes..."

    # We run bl deploy. 
    if bl deploy; then
        print_success "Deployment and Remote Build successful"
    else
        print_error "Deployment failed"
        print_info "If this failed due to Docker missing locally, verify if your Blaxel CLI version supports pure remote builds."
        print_info "Alternative: Push this code to GitHub and connect the repo in the Blaxel Console."
        exit 1
    fi

    sleep 3
}

get_image_id() {
    print_header "Retrieving Image ID"

    print_info "Fetching sandbox details..."

    # Retrieve the image ID using bl CLI
    # We look for the sandbox we just named in blaxel.toml
    IMAGE_ID=$(bl get sandboxes ${SANDBOX_NAME} -ojson 2>/dev/null | grep -o '"image": *"[^"]*"' | cut -d'"' -f4 | head -n 1)

    if [ -z "$IMAGE_ID" ]; then
         # Fallback method if json parsing fails
         IMAGE_ID=$(bl get sandboxes ${SANDBOX_NAME} 2>/dev/null | grep "${SANDBOX_NAME}" | awk '{print $2}')
    fi

    if [ -n "$IMAGE_ID" ]; then
        print_success "Image ID retrieved: $IMAGE_ID"
        echo ""
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}Your custom sandbox image ID is:${NC}"
        echo -e "${YELLOW}$IMAGE_ID${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""

        # Update .env file
        if [ -f ".env" ]; then
            if grep -q "MANIM_SANDBOX_IMAGE" .env; then
                sed -i.bak "s|^MANIM_SANDBOX_IMAGE=.*|MANIM_SANDBOX_IMAGE=$IMAGE_ID|" .env
                rm .env.bak 2>/dev/null || true
                print_success ".env file updated"
            else
                echo "" >> .env
                echo "# Blaxel Custom Sandbox Image" >> .env
                echo "MANIM_SANDBOX_IMAGE=$IMAGE_ID" >> .env
                print_success ".env file updated"
            fi
        else
            echo "MANIM_SANDBOX_IMAGE=$IMAGE_ID" > .env
            print_success "Created .env file"
        fi
    else
        print_warning "Could not verify image ID automatically."
        echo "Run: bl get sandboxes"
    fi
}

main() {
    echo -e "${BLUE}"
    cat << "EOF"
    ╔═══════════════════════════════════════════════════╗
    ║   Blaxel Remote Build & Deploy                    ║
    ║   (Zero Local Storage Mode)                       ║
    ╚═══════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"

    check_prerequisites
    create_config
    deploy_to_blaxel
    get_image_id
    
    echo -e "\n${GREEN}Done! You can now use your sandbox.${NC}"
}

main "$@"