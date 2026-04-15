#!/bin/bash

set +e
###############################################
BLEND_FILE=$@
###############################################
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Set ANIMATION variable based on frame range
if [ "${frame_start}" == "${frame_end}" ]; then
  ANIMATION=false
else
  ANIMATION=true
fi

${SCRIPT_DIR}/job_init.sh ${BLEND_FILE}
###############################################
if [ "${ANIMATION}" = "false" ]; then
  FRAME=${frame_start}
  FRAME_CMD="--render-frame ${FRAME}"
fi
###############################################
if [ ${#work_dir} -ge 1  ]; then
  cd ${work_dir}
  mkdir -p job
  cd job

  if [ ${frame_start} == ${FRAME}  ]; then  
    qstat -fx ${PBS_JOBID} > ${work_dir}.job
  fi  
fi
###############################################
ROOT_DIR=${PWD}/../

LOG_DIR=${ROOT_DIR}/log
IN_DIR=${ROOT_DIR}/in
OUT_DIR=${ROOT_DIR}/out
CACHE_DIR=${ROOT_DIR}/cache

if [ "${ANIMATION}" = "false" ]; then
  LOG=${LOG_DIR}/${FRAME}.log
  ERR=${LOG_DIR}/${FRAME}.err
  LOG_XORG=${LOG_DIR}/${FRAME}_XORG.log
  ERR_XORG=${LOG_DIR}/${FRAME}_XORG.err
fi

###############################################

mkdir -p ${LOG_DIR}
mkdir -p ${IN_DIR}
mkdir -p ${OUT_DIR}
mkdir -p ${CACHE_DIR}

###############################################

if [ "${ANIMATION}" = "false" ]; then
  ~/blender/blender --factory-startup --enable-autoexec -noaudio --background ${IN_DIR}/${BLEND_FILE} -E CYCLES -P ${SCRIPT_DIR}/use_gpu.py --render-output ${OUT_DIR}/###### ${FRAME_CMD} >> ${LOG} 2>> ${ERR}
else
  export BLEND_FILE frame_start frame_end max_jobs use_mpi
  export IN_DIR OUT_DIR LOG_DIR SCRIPT_DIR
  mpirun ${SCRIPT_DIR}/mpi_gpu_bind.sh
fi

###############################################
${SCRIPT_DIR}/job_finish.sh ${BLEND_FILE}