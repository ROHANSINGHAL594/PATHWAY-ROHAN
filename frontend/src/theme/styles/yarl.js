import { cssVarRgba } from 'lib/utils';

const yarl = (theme) => ({
  '& .yarl__container': {
    '--yarl__container_background_color': cssVarRgba(theme.vars.palette.grey['950Channel'], 0.9),
    backdropFilter: 'blur(4px)',
    '.yarl__navigation_next, .yarl__navigation_prev': {
      padding: theme.spacing(1),
      backgroundColor: cssVarRgba(theme.vars.palette.common.whiteChannel, 0.15),
      borderRadius: 99,
      marginLeft: theme.spacing(3),
      marginRight: theme.spacing(3),
      [`${theme.breakpoints.up('md')}`]: {
        marginLeft: theme.spacing(5),
        marginRight: theme.spacing(5),
      },
      filter: 'none',
      '.yarl__icon': {
        '--svg': `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='%23000' d='M12.6 12L8 7.4L9.4 6l6 6l-6 6L8 16.6z'/%3E%3C/svg%3E");`,
        color: theme.vars.palette.common.white,
        width: 20,
        height: 20,
      },
    },
    '.yarl__toolbar': {
      padding: theme.spacing(3),
      [`${theme.breakpoints.up('md')}`]: {
        padding: theme.spacing(5),
      },
      '.yarl__button': {
        padding: 9,
        borderRadius: 8,
        filter: 'none',
        '.yarl__icon': {
          color: theme.vars.palette.common.white,
          width: 24,
          height: 24,
          maskRepeat: 'no-repeat',
          maskSize: '100% 100%',
          backgroundColor: 'currentColor',
        },
      },
      '.yarl__button[title="Play"]': {
        display: 'none',
      },
    },
    '.yarl__carousel_with_slides': {
      '.yarl__slide': {
        padding: theme.spacing(3),
        paddingTop: theme.spacing(11.25),
        [`${theme.breakpoints.up('md')}`]: {
          padding: theme.spacing(5),
          paddingTop: theme.spacing(15.25),
        },
        '.yarl__slide_title_container': {
          backgroundColor: 'transparent',
          padding: theme.spacing(3),
          [`${theme.breakpoints.up('md')}`]: {
            padding: theme.spacing(5),
          },
          '.yarl__slide_title': {
            fontSize: theme.typography.h5.fontSize,
            fontWeight: theme.typography.h5.fontWeight,
            lineHeight: theme.typography.h5.lineHeight,
            color: theme.vars.palette.common.white,
          },
        },
        '.yarl__slide_wrapper > img, .yarl__slide_wrapper > video': {
          borderRadius: theme.shape.borderRadius * 2,
          overflow: 'hidden',
        },
        '.yarl__fullsize': {
          '.yarl__slide_image': {
            objectFit: 'contain',
          },
        },
      },
    },
  },
  '& .yarl__thumbnails_container': {
    '--yarl__thumbnails_container_background_color': cssVarRgba(
      theme.vars.palette.grey['950Channel'],
      0.9,
    ),
    backdropFilter: 'blur(4px)',

    '.yarl__thumbnails_track': {
      '--yarl__thumbnails_thumbnail_gap': theme.spacing(1),

      '.yarl__thumbnails_thumbnail': {
        '--yarl__thumbnails_thumbnail_background': theme.vars.palette.common.black,
        '--yarl__thumbnails_thumbnail_border_color': theme.vars.palette.divider,
        '--yarl__thumbnails_thumbnail_active_border_color': theme.vars.palette.primary.main,
        '--yarl__thumbnails_thumbnail_border_radius': theme.spacing(1),
        '--yarl__thumbnails_thumbnail_padding': 0,
        '--yarl__thumbnails_thumbnail_width': theme.spacing(16.875),

        '&.yarl__thumbnails_thumbnail_active': {
          borderWidth: '2px',
        },

        '.yarl__slide_image': {
          objectFit: 'cover',
          width: '100%',
          height: '100%',
        },
        video: {
          objectFit: 'cover',
          width: '100%',
          height: '100%',
        },
      },
    },

    '.yarl__thumbnails_vignette': {
      background: 'none !important',
    },
  },
});

export default yarl;
