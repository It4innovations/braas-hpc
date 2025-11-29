#!/bin/bash

set +e
###############################################
BLEND_FILE=$@
###############################################
if [ ${frame_start} == ${frame_end}  ]; then
  FRAME=${frame_start}
  FRAME_CMD="--render-frame ${FRAME}"
else
  FRAME=$(( ( ${SLURM_ARRAY_TASK_ID} - 1 ) + ${frame_start} ))
  FRAME_CMD="-s ${FRAME} -e ${frame_end} -j ${max_jobs} -a"
fi
###############################################
if [ ${#job_arrays} -ge 1  ]; then
  FRAME=${SLURM_ARRAY_TASK_ID}
  FRAME_CMD="--render-frame ${FRAME}"
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
#ml Blender/${blender_version}
#ml apptainer
ml CUDA
ml Mesa
###############################################
if [ ${use_xorg} == "True"  ]; then
  Xorg :0 >> ${LOG_XORG} 2>> ${ERR_XORG} &
  sleep 10 # wait on xorg
  export DISPLAY=:0
fi
###############################################

#apptainer exec -B /scratch -B /mnt -B /apps -B ${CUDA_ROOT}:/usr/local/cuda --nv /apps/all/OS/Ubuntu/ubuntu_blender/ubuntu_blender.img /apps/all/Blender/${blender_version}/
~/blender/blender --factory-startup --enable-autoexec -noaudio --background ${IN_DIR}/${BLEND_FILE} -E CYCLES -P ~/braas-hpc/scripts/karolina-slurm/use_gpu.py --render-output ${OUT_DIR}/###### ${FRAME_CMD} >> ${LOG} 2>> ${ERR}
