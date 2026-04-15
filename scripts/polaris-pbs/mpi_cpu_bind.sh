#!/bin/bash

NODEID=$(hostname -s)
echo "Process $PMI_RANK on node $NODEID, Using CPU"

# Check if running in animation mode (BLEND_FILE is set)
if [ -n "$BLEND_FILE" ]; then
  # Calculate frame based on MPI rank
  FRAME=$(( $PMI_RANK + ${frame_start} ))
  FRAME_CMD="-s ${FRAME} -e ${frame_end} -j ${max_jobs} -a"
  
  # Set log files for this frame
  LOG=${LOG_DIR}/${FRAME}.log
  ERR=${LOG_DIR}/${FRAME}.err
  
  # Execute blender for this frame
  # ~/blender/blender --factory-startup --enable-autoexec -noaudio --background ${IN_DIR}/${BLEND_FILE} -E CYCLES -P ${SCRIPT_DIR}/use_gpu.py --render-output ${OUT_DIR}/###### ${FRAME_CMD} >> ${LOG} 2>> ${ERR}
  ~/blender/blender --factory-startup --enable-autoexec -noaudio --background ${IN_DIR}/${BLEND_FILE} -E CYCLES --render-output ${OUT_DIR}/###### ${FRAME_CMD} >> ${LOG} 2>> ${ERR}

  echo "Process $PMI_RANK on node $NODEID, Using CPU" >> ${LOG} 2>> ${ERR}
else
  # Original behavior: execute passed command
  $@
fi