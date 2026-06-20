import colorPicker from 'theme/styles/colorPicker';
import echart from 'theme/styles/echart';
import emojiMart from 'theme/styles/emojiMart';
import keyFrames from 'theme/styles/keyFrames';
import notistack from 'theme/styles/notistack';
import popper from 'theme/styles/popper';
import prism from 'theme/styles/prism';
import projectTimelineChart from 'theme/styles/projectTimelineChart';
import reactFc from 'theme/styles/react-fc';
import reactDatepicker from 'theme/styles/reactDatepicker';
import simplebar from 'theme/styles/simplebar';
import svelteGanttChart from 'theme/styles/svelteGanttChart';
import swiper from 'theme/styles/swiper';
import taskTrackChart from 'theme/styles/taskTrackChart';
import vibrantNav from 'theme/styles/vibrantNav';
import yarl from 'theme/styles/yarl';

const CssBaseline = {
  defaultProps: {},
  styleOverrides: (theme) => ({
    '*': {
      scrollbarWidth: 'thin',
      '&::-webkit-scrollbar': {
        width: '8px',
        height: '8px',
      },
      '&::-webkit-scrollbar-track': {
        background: 'transparent',
      },
      '&::-webkit-scrollbar-thumb': {
        background: 'transparent',
        borderRadius: '4px',
      },
      '&:hover::-webkit-scrollbar-thumb': {
        background: theme.palette.mode === 'dark' 
          ? 'rgba(255, 255, 255, 0.2)' 
          : '#cbd5e0',
      },
      '&::-webkit-scrollbar-thumb:hover': {
        background: theme.palette.mode === 'dark' 
          ? 'rgba(255, 255, 255, 0.3)' 
          : '#a0aec0',
      },
    },
    'input:-webkit-autofill': {
      WebkitBoxShadow: `0 0 0px 40rem ${theme.vars.palette.background.elevation2} inset !important`,
      transition: 'background-color 5000s ease-in-out 0s',
    },
    'input:-webkit-autofill:hover': {
      WebkitBoxShadow: `0 0 0px 40rem ${theme.vars.palette.background.elevation3} inset !important`,
    },
    body: {
      scrollbarColor: `${theme.vars.palette.background.elevation4} transparent`,
      [`h1, h2, h3, h4, h5, h6, p`]: {
        margin: 0,
      },
      fontVariantLigatures: 'none',
      [`[id]`]: {
        scrollMarginTop: 82,
      },
    },
    ...simplebar(theme),
    ...swiper(theme),
    ...notistack(theme),
    ...keyFrames(),
    ...prism(),
    ...echart(),
    ...popper(theme),
    ...colorPicker(theme),
    ...reactDatepicker(theme),
    ...vibrantNav(theme),
    ...svelteGanttChart(theme),
    ...projectTimelineChart(theme),
    ...taskTrackChart(theme),
    ...reactFc(theme),
    ...emojiMart(theme),
    ...yarl(theme),
  }),
};

export default CssBaseline;
