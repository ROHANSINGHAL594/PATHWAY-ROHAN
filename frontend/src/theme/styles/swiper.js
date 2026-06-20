import 'swiper/css';
import 'swiper/css/pagination';

const swiper = (theme) => ({
  '& .swiper': {
    '& .swiper-pagination': {
      '& .swiper-pagination-bullet': {
        backgroundColor: theme.vars.palette.common.white,
        opacity: 0.5,

        '&.swiper-pagination-bullet-active': {
          backgroundColor: theme.vars.palette.primary.main,
          width: theme.spacing(3),
          borderRadius: theme.spacing(0.5),
          opacity: 1,
        },
      },
    },
  },
  '& .swiper-button-disabled': {
    opacity: 0.5,
    pointerEvents: 'none',
  },
});
export default swiper;
