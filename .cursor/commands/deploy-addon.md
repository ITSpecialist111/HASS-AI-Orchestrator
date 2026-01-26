# Deploy Add-on

## Purpose
Builds, packages, and deploys the AI Orchestrator add-on to Home Assistant, handling all necessary build steps and validations.

## Usage
`/deploy-addon [environment]`

Environments:
- `local` - Deploy to local HA instance (default)
- `test` - Build test image with validation
- `production` - Full production build with optimization

## Instructions for Agent

When this command is invoked:

1. **Pre-Deployment Checks**:
   - Run linter on Python files
   - Execute smoke tests
   - Verify configuration files are valid
   - Check all required environment variables
   - Validate Docker files

2. **Version Management**:
   - Check current version in config.json
   - Ensure CHANGELOG.md is updated
   - Tag commit if production deployment

3. **Build Dashboard**:
   ```bash
   cd ai-orchestrator/dashboard
   npm install
   npm run build
   ```
   - Verify build completes without errors
   - Check bundle size is reasonable

4. **Build Docker Image**:
   ```bash
   cd ai-orchestrator
   docker build -t ghcr.io/itspecialist111/hass-ai-orchestrator:latest .
   ```
   - Use multi-stage build for optimization
   - Tag with version number
   - Verify image size

5. **Run Pre-Deployment Tests**:
   ```bash
   docker run --rm ai-orchestrator:test pytest -m smoke -v
   ```
   - All tests must pass before deployment

6. **Deploy Based on Environment**:
   
   **Local**:
   - Stop existing add-on
   - Copy files to HA add-on directory
   - Restart add-on
   - Check logs for successful startup
   
   **Production**:
   - Push image to container registry
   - Update repository.yaml
   - Create GitHub release
   - Notify users of update

7. **Post-Deployment Validation**:
   - Check add-on starts successfully
   - Verify web UI is accessible
   - Test agent initialization
   - Confirm HA integration works
   - Monitor logs for errors

8. **Rollback Plan**:
   - Keep previous image tagged
   - Document rollback procedure
   - If critical errors, revert immediately

## Expected Outcome
- Add-on successfully built
- All tests passing
- Deployed to target environment
- Web UI accessible and functional
- Agents running correctly
- No critical errors in logs

## Build Artifacts
- Docker image: `ghcr.io/itspecialist111/hass-ai-orchestrator:[version]`
- Dashboard bundle: `ai-orchestrator/dashboard/build/`
- Version tag: `v[x.y.z]`

## Deployment Checklist
- [ ] Code linted and formatted
- [ ] All tests passing
- [ ] CHANGELOG.md updated
- [ ] Version bumped in config.json
- [ ] Dashboard builds successfully
- [ ] Docker image builds
- [ ] Smoke tests pass in container
- [ ] Add-on starts in HA
- [ ] Web UI accessible
- [ ] Agents initialize correctly
