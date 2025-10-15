#!/bin/bash

set +e
###############################################
BLEND_FILE=$@
###############################################
if [ ${#work_dir} -ge 1  ]; then
  cd ${work_dir}
  mkdir -p jsob
  cd job
fi
###############################################
ROOT_DIR=${PWD}/../

LOG_DIR=${ROOT_DIR}/log
IN_DIR=${ROOT_DIR}/in
OUT_DIR=${ROOT_DIR}/out
CACHE_DIR=${ROOT_DIR}/cache

LOG=${LOG_DIR}/${FRAME}.log
ERR=${LOG_DIR}/${FRAME}.err

###############################################

mkdir -p ${LOG_DIR}
mkdir -p ${IN_DIR}
mkdir -p ${OUT_DIR}
mkdir -p ${CACHE_DIR}

###############################################
if [ ${#work_dir} -ge 1  ]; then
  sacct --format=JobID%20,Jobname%50,state,Submit,start,end -j ${depends_on##* } > ${work_dir}.job
fi
###############################################


