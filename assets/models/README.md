# Custom Models Directory

Place custom Gazebo models here.

## Model Structure

Each model should have the following structure:

```
model_name/
├── model.config    # Model metadata
├── model.sdf       # Model definition
├── meshes/         # 3D mesh files (.dae, .stl)
└── materials/      # Textures and materials
    └── textures/
```

## Example model.config

```xml
<?xml version="1.0"?>
<model>
  <name>My Custom Model</name>
  <version>1.0</version>
  <sdf version="1.9">model.sdf</sdf>
  <description>
    A custom model for simulation
  </description>
</model>
```

## Adding Models to Gazebo

After placing your model here, add the path to your environment:

```bash
export GZ_SIM_RESOURCE_PATH=$GZ_SIM_RESOURCE_PATH:/path/to/this/models
```

Or copy to the system models directory:

```bash
sudo cp -r my_model /usr/local/share/ardupilot_gazebo/models/
```

## Available Models from SITL_Models

If you cloned SITL_Models, these are available:

- `mini_talon_vtail` - V-tail fixed wing
- `skywalker_x8` - Flying wing
- `bicopter_with_ardupilot` - Bicopter
- `wildthumper` - Rover
- And more...

See: https://github.com/ArduPilot/SITL_Models
