# AI-SPRINT DESIGN

Initial implementation of the AI-SPRINT design tool. 

Currently implemented functionalities:
- Creation of new AI-SPRINT applications from template (based on cookiecutter)
- AI-SPRINT annotations (security annotations must be added)
- Parsing of AI-SPRINT annotations (security annotations must be added)
- Creation of AI-SPRINT designs (base + partitions
- Generation of configuration files for each design given the provided annotations:
    - Currently only 'exec_time'-derived constraints for monitoring tool
- Some error checking:
    - DAG format
    - Annotations syntax. Implemented for:
        - component_name
        - exec_time
        - expected_throughput
        - partitionable_model 
## Quick-Start
---

### Step1: Install Requirements (Python 3.8.10):
```
python3 -m pip install cookiecutter==2.1.1
```

### Step2: Install AI-SPRINT 
```
git clone https://gitlab.polimi.it/ai-sprint/ai-sprint-design.git
cd ai-sprint-design
python3 -m pip install . 
```

### Step3: Try --help 
```
aisprint --help
```

## Example1: Create new application
```
aisprint new-application --application_name NAME
```

## Example2: Parse annotations and create designs 
### example application in 'examples'
```
aisprint design --application_dir ./NAME
```
## Docker
---
### Step1: Build the Docker image
```
git clone https://gitlab.polimi.it/ai-sprint/ai-sprint-design.git
cd ai-sprint-design
docker build -t registry.gitlab.polimi.it/ai-sprint/ai-sprint-design -f docker/Dockerfile .
```
### (Step1b): Push the Docker image to the container registry
```
docker push registry.gitlab.polimi.it/ai-sprint/ai-sprint-design
```

### Step2: Try design --help
```
docker run registry.gitlab.polimi.it/ai-sprint/ai-sprint-design aisprint --help
```

### Example1: Create new application
```
docker run registry.gitlab.polimi.it/ai-sprint/ai-sprint-design aisprint new-application --application_name NAME 
```
```
### Example2: Parse annotations and create designs 
```
docker run -v /PATH/TO/APPLICATION_DIR/:/NAME registry.gitlab.polimi.it/ai-sprint/ai-sprint-design aisprint design --application_dir NAME
```