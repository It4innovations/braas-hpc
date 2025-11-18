#!/bin/bash

set +e
###############################################
if [ ${#work_dir} -ge 1  ]; then
  cd ${work_dir}
  mkdir -p job
  cd job

  sacct --format=JobID%20,Jobname%50,state,Submit,start,end -j ${SLURM_JOBID} | grep -v "\." > ${work_dir}.job
fi
###############################################
ROOT_DIR=${PWD}/../

LOG_DIR=${ROOT_DIR}/log
IN_DIR=${ROOT_DIR}/in
OUT_DIR=${ROOT_DIR}/out
INTERACTIVE_DIR=${ROOT_DIR}/interactive

LOG=${LOG_DIR}/interactive.log
ERR=${LOG_DIR}/interactive.err
###############################################

mkdir -p ${LOG_DIR}
mkdir -p ${IN_DIR}
mkdir -p ${OUT_DIR}
mkdir -p ${INTERACTIVE_DIR}

###############################################
hostname -s > ${INTERACTIVE_DIR}/hostname.txt
echo "$@" -s > ${INTERACTIVE_DIR}/command.txt
###############################################
#$@
sleep 172800
