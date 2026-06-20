const taskTrackChart = (theme) => {
  const { vars } = theme;

  return {
    '& .sg-task.development': {
      backgroundColor: vars.palette.chBlue[100],
    },
    '& .sg-task.design': {
      backgroundColor: vars.palette.chGreen[100],
    },
    '& .sg-task.research': {
      backgroundColor: vars.palette.chOrange[100],
    },
    '& .sg-task.testing': {
      backgroundColor: vars.palette.chLightBlue[100],
    },
    '& .sg-task.support': {
      backgroundColor: vars.palette.chRed[100],
    },
  };
};

export default taskTrackChart;
