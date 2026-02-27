// 设计令牌 - 全局设计变量

export const COLORS = {
  // 品牌色
  primary: '#667eea',
  primaryLight: '#8fa4f0',
  primaryDark: '#4c63d2',

  // RAG 专属色
  rag: '#722ed1',
  ragLight: '#9254de',
  ragDark: '#531dab',
  ragBg: 'linear-gradient(135deg, #722ed1 0%, #9254de 100%)',

  // 语义色
  success: '#52c41a',
  warning: '#faad14',
  error: '#ff4d4f',
  info: '#1890ff',

  // 背景色
  bgBase: '#f5f7fa',
  bgCard: '#ffffff',
  bgHover: '#f0f2f5',
  bgActive: '#e6f7ff',

  // 边框色
  border: '#e8e8e8',
  borderLight: '#f0f0f0',
  borderDark: '#d9d9d9',

  // 文字色
  textPrimary: '#24292e',
  textSecondary: '#6a737d',
  textTertiary: '#999999',
  textInverse: '#ffffff',
};

export const SPACING = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
};

export const FONT_SIZE = {
  xs: 12,
  sm: 13,
  md: 14,
  lg: 16,
  xl: 18,
  xxl: 24,
};

export const BORDER_RADIUS = {
  sm: 4,
  md: 8,
  lg: 12,
};

export const SHADOWS = {
  sm: '0 1px 4px rgba(0,0,0,0.08)',
  md: '0 2px 8px rgba(0,0,0,0.08)',
  lg: '0 4px 16px rgba(0,0,0,0.12)',
  siderLeft: '2px 0 8px rgba(0,0,0,0.06)',
  siderRight: '-2px 0 8px rgba(0,0,0,0.06)',
};

export const Z_INDEX = {
  divider: 10,
  header: 100,
  modal: 1000,
};

export const TRANSITIONS = {
  default: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
  fast: 'all 0.15s ease',
  opacity: 'opacity 0.2s ease',
};

// Ant Design ConfigProvider theme token
export const antThemeToken = {
  colorPrimary: COLORS.primary,
  colorSuccess: COLORS.success,
  colorWarning: COLORS.warning,
  colorError: COLORS.error,
  colorInfo: COLORS.info,
  borderRadius: BORDER_RADIUS.md,
  borderRadiusLG: BORDER_RADIUS.lg,
  borderRadiusSM: BORDER_RADIUS.sm,
  fontSize: FONT_SIZE.md,
  controlHeight: 36,
  boxShadow: SHADOWS.md,
  boxShadowSecondary: SHADOWS.lg,
};

// Ant Design component-level theme overrides
export const antComponentTheme = {
  Card: {
    headerBg: 'transparent',
    paddingLG: SPACING.xl,
  },
  Tree: {
    titleHeight: 32,
    nodeSelectedBg: COLORS.bgActive,
  },
  Tabs: {
    cardPaddingSM: `${SPACING.sm}px ${SPACING.lg}px`,
  },
};
