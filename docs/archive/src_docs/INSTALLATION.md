# Installation Guide

> **ARCHIVED — superseded.** Canonical install reference for `workspace_next`
> is `docs/onboarding/installation.md`. Errata:
> `governance/audits/2026-05-20_phase3_docs_errata.md`.

Basic setup for ArduPilot SITL with Gazebo Sim on Ubuntu 22.04/24.04.

## Prerequisites

Update system and install required build tools:
- git, cmake, build-essential
- Python 3 development packages
- Standard development libraries

## Step 1: Install Gazebo Harmonic

Add Gazebo repository and install gz-harmonic package. Verify installation with version check.

## Step 2: Install ArduPilot

Clone ArduPilot repository with submodules. Run the prerequisites installation script. Configure and build for SITL using waf.

Build both plane and copter variants as needed.

## Step 3: Install ArduPilot Gazebo Plugin

Install Gazebo development libraries and dependencies. Clone ardupilot_gazebo repository, build with cmake, and install system-wide.

Verify plugin and model installation in appropriate directories.

## Step 4: Configure Environment

Set GZ_SIM_SYSTEM_PLUGIN_PATH and GZ_SIM_RESOURCE_PATH environment variables to point to installed plugin and resources.

Add to shell profile for persistence.

## Step 5: Test Installation

Run sim_vehicle.py with JSON mode for ArduCopter or ArduPlane. Launch Gazebo with appropriate world file in separate terminal.

Verify communication and control response.

## Additional Models

Additional aircraft models may be available from SITL_Models repository. Install as needed for specific use cases.

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues.
