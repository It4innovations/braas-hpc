#!/bin/bash

set +e
###############################################
BLEND_FILE=$@
###############################################
FRAME=${SLURM_ARRAY_TASK_ID}

if [ ${frame_start} == ${frame_end}  ]; then
  FRAME=${frame_start}
fi
###############################################
if [ ${#work_dir} -ge 1  ]; then
  cd ${work_dir}
  mkdir -p job
  cd job
  
  if [ ${frame_start} == ${FRAME}  ]; then  
    sacct --format=JobID%20,Jobname%50,state,Submit,start,end -j ${SLURM_JOBID} | grep -v "\." > ${work_dir}.job
  fi   
fi
###############################################
ROOT_DIR=${PWD}/../

LOG_DIR=${ROOT_DIR}/log
IN_DIR=${ROOT_DIR}/in
OUT_DIR=${ROOT_DIR}/out
CACHE_DIR=${ROOT_DIR}/cache

LOG=${LOG_DIR}/${FRAME}.log
ERR=${LOG_DIR}/${FRAME}.err
LOG_XORG=${LOG_DIR}/${FRAME}_XORG.log
ERR_XORG=${LOG_DIR}/${FRAME}_XORG.err

###############################################

mkdir -p ${LOG_DIR}
mkdir -p ${IN_DIR}
mkdir -p ${OUT_DIR}
mkdir -p ${CACHE_DIR}

###############################################

if [ ${use_xorg} == "True"  ]; then
  #Xorg :0 >> ${LOG_XORG} 2>> ${ERR_XORG} &
  #sleep 10 # wait on xorg
  export DISPLAY=:0
fi
###############################################
if [ ${frame_start} == ${frame_end}  ]; then
    
    ~/blender/blender --factory-startup --enable-autoexec -noaudio --background ${IN_DIR}/${BLEND_FILE} -E BLENDER_WORKBENCH --render-output ${OUT_DIR}/###### --render-frame ${FRAME} >> ${LOG} 2>> ${ERR}

    
else

  if [ ${use_mpi} -ge 2 ]; then

      #script_full_path=$(dirname "$0")
      #srun -n ${use_mpi} ${script_full_path}/run_workbench_mpi.sh ${FRAME} ${frame_start} ${frame_end} ${frame_step} ${blender_version} ${IN_DIR} ${BLEND_FILE} ${OUT_DIR} ${LOG} ${ERR}
      srun /users/${username}/braas-hpc/scripts/lumi-slurm/run_workbench_mpi.sh ${FRAME} ${frame_start} ${frame_end} ${frame_step} ${blender_version} ${IN_DIR} ${BLEND_FILE} ${OUT_DIR} ${LOG} ${ERR}

  else
      
      ~/blender/blender --factory-startup --enable-autoexec -noaudio --background ${IN_DIR}/${BLEND_FILE} -E BLENDER_WORKBENCH --render-output ${OUT_DIR}/###### --render-frame ${FRAME} >> ${LOG} 2>> ${ERR}
  
  fi

fi

