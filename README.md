# BRaaS-HPC (Bheappe Add-on v. 2.0) - Blender Rendering-as-a-Service for HPC

#### BLENDER ADD-ON TO EXTEND ITS CAPABILITIES IN TERMS OF RENDERING ON AN HPC CLUSTER

We provide a Python add-on for Blender that can re-formulate a typical user scene rendering task into a specific HPC computational job, which currently works only as an SSH remote client. This add-on has been developed at [IT4Innovations National Supercomputing Center](https://www.it4i.cz/).

## Key Features
- **Multiple HPC Cluster Support**: Connect to various supercomputing facilities including:
    - Support of Slurm-based HPC clusters:
        - Support of [Barbora](https://www.it4i.cz/en/infrastructure/barbora) supercomputer
        - Support of [Karolina](https://www.it4i.cz/en/infrastructure/karolina) supercomputer
        - Support of [LUMI](https://lumi-supercomputer.eu) supercomputer
        - Support of [Leonardo](https://www.hpc.cineca.it/systems/hardware/leonardo) supercomputer
        - Support of [MareNostrum 5](https://www.bsc.es/marenostrum/marenostrum-5) supercomputer
        - Support of [Vista](https://tacc.utexas.edu/systems/vista) supercomputer
        - Support of [Frontera](https://tacc.utexas.edu/systems/frontera) supercomputer

    - Support of PBS-based HPC clusters:
        - Support of [Polaris](https://www.alcf.anl.gov/polaris) supercomputer
        - Support of [Aurora](https://www.alcf.anl.gov/aurora) supercomputer

- **Flexible Authentication**: Support for multiple SSH connection methods:
  - Paramiko (Python SSH library)
  - AsyncSSH (Asynchronous SSH)
  - System (SSH installed in the user system)

- **Job Management**: 
  - Submit single image or animation rendering jobs
  - Monitor job status in real-time
  - Cancel running jobs
  - Download rendered outputs and log files
  - View detailed job information and progress

- **Resource Configuration**:
  - Configure multiple cluster presets (allocation, partition, queue)
  - Specify walltime, CPU/GPU resources
  - Support for job arrays for parallel frame rendering
  - Customizable working directories per cluster

- **File Handling**:
  - Automatic packing of Blender files with dependencies
  - Support for external file structures
  - Secure file transfer via SSH/SCP

## Requirements

### System Requirements
- **Blender**: Version 4.0.0 or higher
- **Python**: 3.x (bundled with Blender)
- **Operating System**: Windows, Linux, or macOS

### HPC Access Requirements
- Active account on one or more supported HPC clusters
- SSH access credentials (username + private key with passphrase)
- Allocated project/allocation ID on the target cluster
- Network connectivity to the HPC facility

### Python Dependencies
The addon requires the following Python packages (can be installed via the addon preferences):
- `paramiko` - SSH protocol implementation
- `scp` - Secure file copy functionality
- `asyncssh` - Asynchronous SSH client/server  

## Installation

### Step 1: Download the Addon

Download the add-on in zip format: https://github.com/It4innovations/braas-hpc/releases

### Step 2: Install in Blender

1. Open Blender (version 4.0 or higher)

2. Go to **Edit → Preferences** (or **Blender → Preferences** on macOS)

3. Select the **Add-ons** tab

4. Click **Install...** button at the top

5. Navigate to the `braas_hpc.zip` file and install it

6. Enable the addon by checking the checkbox next to **System: BRaaS-HPC**

### Step 3: Install Python Dependencies

1. In Blender Preferences, expand the **BRaaS-HPC** addon settings

2. Scroll to the **Dependencies** section

3. Click **Install Dependencies** button

4. Wait for the installation to complete (this may take a few minutes)

5. Restart Blender after installation

### Step 4: Configure HPC Access

BRaaS-HPC add-on properties can be set in ***Blender Preferences*** menu, see figure below.
    
![](img/preferences.png)


#### Add Cluster Preset

1. In the addon preferences, scroll to the **Cluster Presets** section

2. Click the **+** button to add a new cluster preset

3. Configure the preset with:
   - **Cluster Name**: Select your target HPC cluster
   - **Allocation Name**: Your project/allocation ID
   - **Partition Name**: Queue/partition to use
   - **Job Type**: CPU or GPU rendering
   - **Username**: Your HPC username
   - **SSH Library**: Choose authentication method (AsyncSSH recommended)
   - **Private Key Path**: Path to your SSH private key file
   - **Private Key Password**: Passphrase for your private key

4. Enable the preset by checking the **Is Enabled** checkbox (after **Find Working Directories**)

#### Configure Job Storage

1. Set **Job Storage Path**: Local directory where job files will be stored
   - Example: `C:\Users\YourName\BRaaS_Jobs` (Windows)
   - Example: `/home/yourname/braas_jobs` (Linux)

2. The addon will create subdirectories for each job submission

#### Find Working Directories

1. Click the **Find Working Dirs** button to automatically discover your project directories on configured clusters

2. This will populate the **Working Dir** field for each enabled cluster preset

#### Install Scripts on Clusters

1. Configure the **Git Repository (Scripts)** field with the rendering scripts repository:
   - Default: `https://github.com/It4innovations/braas-hpc.git`
   - Branch: `main`

2. Set the **Link (Blender)** to the Blender version to use on the cluster:
   - Example: `https://ftp.nluug.nl/pub/graphics/blender/release/Blender4.5/blender-4.5.5-linux-x64.tar.xz`

3. Click **Install scripts and Blender on the cluster(s)** button

4. After successful installation, check the **Manual Installation / Scripts already installed** checkbox

#### Test Connection

1. Click the **Test Connections** button to verify connectivity to all enabled cluster presets

2. Check the Blender Info Editor or System Console for connection results


## Usage

Once configured, you can submit rendering jobs directly from Blender's Render Properties panel. Add-on supports *Cycles* rendering only. Thus it is available only in case *Cycles* is selected as *Render Engine*.

***BRaaS-HPC*** menu is divided in ***Status***, ***New Job*** and ***Jobs*** menus.
See figure below. 

![](img/addon-1.png)

***Status*** menu provides user with information about progress of ongoing action, e.g., sending query for job update etc.

***New Job*** menu enables to define details about a rendering job and submit this job to the selected remote cluster. The particular cluster, allocation and HW partition is selected in the correspoding table. Users can set a project name, specify their email to receive notifications when job is done (only in case you have been assigned computational resources and this email address was used), specify execution parameters (see below) and choose whether to render only a single image or sequence of images (animation).

***Jobs*** menu provides an overview about the submitted jobs showing their actual states and target remote machines. If some particular job from the list in the ***Jobs*** menu is selected, users can download the results to their local folder and browse them by opening a file explorer via a corresponding button. Final and partial results may be downloaded if exist. Jobs in the list that are not finalized can be cancelled on demand by selection the row with the particular job and pressing "Cancel" button. Pressing "Refresh" button refreshes the statuses of jobs. Pressing this button is required from time to time because this action is not provided automatically. Sometimes users are encouraged to perform the refresh action, e.g., after submitting a new job because it may take a while until a new job is initiated on the remote site and can be monitored.

![](img/addon-2.png)

### Accessing the BRaaS-HPC Panel

1. Open a Blender project with a scene ready to render

2. Go to the **Render Properties** tab (camera icon in Properties panel)

3. Scroll down to find the **BRaaS-HPC** section

4. Expand the **New Job** sub-panel

### Submitting a Rendering Job

#### Step 1: Select Cluster Configuration

1. In the **New Job** panel, you'll see a table of available cluster presets

2. Select the cluster preset you want to use by clicking on it

3. The table shows:
   - **Allocation**: Your project ID
   - **Cluster**: The HPC facility name
   - **Partition**: Queue/partition
   - **Type**: CPU or GPU

#### Step 2: Configure Job Parameters

1. **Job Project**: Enter a descriptive name for your job (max 25 characters)

2. **Job Email**: (Optional) Email address for job notifications

3. **Render Type**: Choose between:
   - **Image**: Render a single frame
   - **Animation**: Render a frame range

4. **File Type**: Select how to package your Blender file:
   - **Packed .blend file**: All textures and dependencies packed into one file (recommended)
   - **Sources in directory**: Separate .blend file with external dependencies

5. **Walltime [minutes]**: Maximum time for the job to run (1-2880 minutes)
   - Set this based on your scene complexity
   - Jobs exceeding walltime will be terminated

#### Step 3: Configure Frame Settings

**For Single Image Rendering:**
- The current frame (`frame_current`) will be rendered

**For Animation Rendering:**
- **Max Jobs**: Maximum number of parallel rendering tasks (1-10000)
- **Frame Start**: First frame to render
- **Frame End**: Last frame to render
- **Job Arrays**: (Optional) Custom frame array specification
  - Example: `1-100:10` renders frames 1, 11, 21, ..., 91
  - Leave empty for automatic frame distribution

#### Step 4: Submit the Job

1. Review all settings carefully

2. Click the **Submit Job** button (with animation icon)

3. The addon will:
   - Pack your Blender file (if needed)
   - Upload files to the HPC cluster
   - Submit the job to the queue
   - Return a Job ID for tracking

4. Monitor the status bar at the top of the panel:
   - **Status**: Shows current operation (IDLE, UPLOADING, RUNNING, etc.)
   - **Progress bar**: Displays operation progress

### Monitoring Jobs

#### View Job List

1. Expand the **Jobs** sub-panel in BRaaS-HPC section

2. Click **List Jobs** to retrieve all your submitted jobs

3. The jobs list displays:
   - **ID**: Unique job identifier
   - **Project**: Job name
   - **Cluster**: Target HPC facility
   - **State**: Job status (CONFIGURING, QUEUED, RUNNING, FINISHED, FAILED, CANCELED)

#### Check Job Details

1. Select a job from the list by clicking on it

2. Click **Show Info** to view detailed job information:
   - Submission time
   - Start time
   - End time
   - Allocated resources
   - All job parameters

#### Download Results

1. Select a finished job from the list

2. Click **Download Files** to retrieve:
   - Rendered output images (in `/out` folder)
   - Log files (in `/log` folder)
   - Job information files (in `/job` folder)

3. Files will be downloaded to your local Job Storage Path in a timestamped subfolder

#### Cancel a Job

1. Select a running or queued job

2. Click **Cancel Job** to terminate the job on the cluster

3. The job state will change to CANCELED

### Managing Jobs

- **Refresh Status**: Click **List Jobs** again to update job states
- **Filter Jobs**: Use the search box above the job list to filter by name
- **Abort Operation**: If an operation is stuck, click the **Cancel** button (X icon) next to the progress bar


# Usage & User Projects
- **Chora** by Gaia Radić: [Aksioma](https://aksioma.org/chora), [GaiaRadic](https://www.gaiaradic.com/chora)
- **Dejvický kampus** by Michal Faltýnek: [Akademik](https://www.vsb.cz/magazin/cs/detail-novinky/?reportId=49300)
- **Holograms**: [Youtube](https://www.youtube.com/watch?v=PKPoO_0nNYA), [GitLab (private project)](https://code.it4i.cz/svo0120/holograms)
- **InfraLab Portfolio**: [IT4I](https://www.it4i.cz/en/infrastructure/visualization-and-virtual-reality-labs/examples-of-our-visualizations)
- **InnovAIte Slovakia: Illuminating Pathways for AI‑Driven Breakthroughs**: [InnovAIte](https://innovaite.sk/)
- **Massively parallel implementation of algorithms for computer graphics**: PhD Thesis by Milan Jaroš
- **Railway simulator for obsacle detection project**: [IT4I News 1](https://www.it4i.cz/en/about/infoservice/news/railway-simulator-for-obsacle-detection-project), [IT4I News 2](https://www.it4i.cz/en/about/infoservice/news/simulator-of-railway-track-conditions-can-help-enhance-railway-safety), [GitLab](https://code.it4i.cz/tacr/simulator)
- **Research Excellence For REgion Sustainability and High-tech Industries**: [REFRESH](https://www.smaragdova.cz/refresh/)
- **Scalable Parallel Astrophysical Codes for Exascale**: [SPACE CoE](https://www.space-coe.eu)
- **Spring**: [Youtube](https://www.youtube.com/watch?v=WhWc3b3KhnY&t=1s)
- **Synthetic SEM image generator**: [GitLab](https://code.it4i.cz/SEM-Image/segment_sem_images_hctpm)
- **Workflow for high-quality visualisation of large-scale CFD simulations by volume rendering**: [Paper](https://doi.org/10.1016/j.advengsoft.2024.103822), [Zenodo](https://zenodo.org/records/13639352)
- **ELI Beamlines**: [9th Users’ Conference of IT4Innovations](https://events.it4i.cz/event/346/attachments/820/2889/01_Valenta_Petr_Machine-learning%20optimization%20of%20laser-driven%20electron%20accelerators.pdf)
- ...


# License
This software is licensed under the terms of the [GNU General Public License](https://github.com/It4innovations/braas-hpc/blob/main/LICENSE).


# Acknowledgement
This work was supported by the Ministry of Education, Youth and Sports of the Czech Republic through the e-INFRA CZ (ID:90254).

This work was supported by the SPACE project. This project has received funding from the European High- Performance Computing Joint Undertaking (JU) under grant agreement No 101093441. This project has received funding from the Ministry of Education, Youth and Sports of the Czech Republic (ID: MC2304).

