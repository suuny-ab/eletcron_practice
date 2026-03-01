import { useState, useMemo, useEffect } from 'react';
import {
  CheckCircleOutlined, LoadingOutlined, CloseCircleOutlined,
  BulbOutlined, SearchOutlined, DownOutlined, UpOutlined,
  InfoCircleOutlined, FileTextOutlined,
} from '@ant-design/icons';
import { COLORS } from '../../styles/tokens';

// stage → 中文标签
const STAGE_LABELS = {
  classifying: '意图分析',
  checking_doc: '文档检查',
  analyzing: '问题分析',
  retrieving: '知识检索',
  evaluating: '结果评估',
  rewriting: '策略优化',
  generating: '生成回答',
  advising: '文档分析',
  editing: '文档编辑',
  formatting: '文档格式化',
};

/**
 * 将 processMessages 分组为逻辑步骤
 */
function groupMessagesToSteps(messages, isStreaming) {
  const steps = [];
  let stepId = 0;

  for (let i = 0; i < messages.length; i++) {
    const msg = messages[i];

    if (msg.type === 'status') {
      const stage = msg.data?.stage || '';
      const label = STAGE_LABELS[stage] || msg.content || '执行中';
      const round = msg.data?.round || null;

      const step = {
        id: `s${stepId++}`,
        label,
        status: 'completed',
        thinking: null,
        sources: null,
        prompt: null,
        error: null,
        round,
      };

      // 查看下一条是否为 thinking
      if (i + 1 < messages.length && messages[i + 1].type === 'thinking') {
        step.thinking = messages[i + 1].content;
        i++; // 跳过 thinking
      }

      steps.push(step);
      continue;
    }

    if (msg.type === 'thinking') {
      // 独立 thinking（未跟在 status 后）
      if (steps.length > 0) {
        const lastStep = steps[steps.length - 1];
        // 追加而非覆盖：如果上一步已有 thinking，则拼接
        if (lastStep.thinking) {
          lastStep.thinking += '\n' + msg.content;
        } else {
          lastStep.thinking = msg.content;
        }
      } else {
        steps.push({
          id: `s${stepId++}`,
          label: '思考',
          status: 'completed',
          thinking: msg.content,
          sources: null, prompt: null, error: null, round: null,
        });
      }
      continue;
    }

    if (msg.type === 'sources') {
      if (steps.length > 0) {
        steps[steps.length - 1].sources = msg.data;
      }
      continue;
    }

    if (msg.type === 'prompt') {
      steps.push({
        id: `s${stepId++}`,
        label: '需要操作',
        status: 'completed',
        thinking: null, sources: null,
        prompt: msg.content,
        error: null, round: null,
      });
      continue;
    }

    if (msg.type === 'error') {
      if (steps.length > 0) {
        steps[steps.length - 1].status = 'error';
        steps[steps.length - 1].error = msg.content;
      } else {
        steps.push({
          id: `s${stepId++}`,
          label: '执行失败',
          status: 'error',
          thinking: null, sources: null, prompt: null,
          error: msg.content,
          round: null,
        });
      }
      continue;
    }
  }

  // 流式状态下最后一步标记为 active
  if (isStreaming && steps.length > 0) {
    const last = steps[steps.length - 1];
    if (last.status !== 'error') {
      last.status = 'active';
    }
  }

  return steps;
}

/**
 * 生成摘要文本：意图分析 → 知识检索 2 轮 → 生成回答
 */
function generateSummary(steps) {
  const parts = [];
  let retrievalRounds = 0;

  for (const step of steps) {
    if (step.label === '知识检索') {
      retrievalRounds++;
      continue;
    }
    // 在检索结束后插入合并的检索摘要
    if (retrievalRounds > 0 && step.label !== '结果评估' && step.label !== '策略优化') {
      parts.push(retrievalRounds > 1 ? `知识检索 ${retrievalRounds} 轮` : '知识检索');
      retrievalRounds = 0;
    }
    // 跳过评估和重写，它们是检索子步骤
    if (step.label === '结果评估' || step.label === '策略优化') {
      continue;
    }
    parts.push(step.label);
  }

  // 末尾检索未结算
  if (retrievalRounds > 0) {
    parts.push(retrievalRounds > 1 ? `知识检索 ${retrievalRounds} 轮` : '知识检索');
  }

  return parts.join(' → ') || '执行完成';
}

// ===== 单步骤 =====

function StepItem({ step, isLast }) {
  const [thinkingVisible, setThinkingVisible] = useState(false);

  const iconStyle = {
    fontSize: 14,
    flexShrink: 0,
    position: 'relative',
    zIndex: 1,
  };

  const icon = step.status === 'active'
    ? <LoadingOutlined spin style={{ ...iconStyle, color: COLORS.primary }} />
    : step.status === 'error'
      ? <CloseCircleOutlined style={{ ...iconStyle, color: COLORS.error }} />
      : <CheckCircleOutlined style={{ ...iconStyle, color: COLORS.success }} />;

  const lineColor = step.status === 'completed' ? COLORS.success
    : step.status === 'active' ? COLORS.primary
    : COLORS.error;

  return (
    <div style={{ position: 'relative', paddingBottom: isLast ? 0 : 2 }}>
      {/* 竖线 */}
      {!isLast && (
        <div style={{
          position: 'absolute',
          left: 6,
          top: 16,
          bottom: 0,
          width: 2,
          background: lineColor,
          opacity: step.status === 'active' ? 0.4 : 0.6,
        }} />
      )}

      {/* 标题行 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, minHeight: 22 }}>
        {icon}
        <span style={{
          fontSize: 12,
          color: step.status === 'active' ? COLORS.primary : COLORS.textPrimary,
          fontWeight: step.status === 'active' ? 500 : 400,
          lineHeight: '16px',
        }}>
          {step.label}
          {step.round != null && (
            <span style={{
              marginLeft: 4,
              fontSize: 10,
              color: COLORS.textTertiary,
              fontWeight: 400,
            }}>
              (第{step.round}轮)
            </span>
          )}
        </span>
      </div>

      {/* 详情区 */}
      <div style={{ marginLeft: 22, marginTop: 2 }}>
        {/* thinking */}
        {step.thinking && (
          <div style={{ marginBottom: 2 }}>
            <div
              onClick={() => setThinkingVisible(!thinkingVisible)}
              style={{
                fontSize: 11,
                color: COLORS.textSecondary,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 3,
                userSelect: 'none',
              }}
            >
              <BulbOutlined style={{ fontSize: 10 }} />
              <span>思考</span>
              {thinkingVisible
                ? <UpOutlined style={{ fontSize: 8 }} />
                : <DownOutlined style={{ fontSize: 8 }} />}
            </div>
            {thinkingVisible && (
              <div style={{
                marginTop: 3,
                padding: '4px 8px',
                background: COLORS.bgHover,
                borderRadius: 4,
                fontSize: 11,
                color: COLORS.textSecondary,
                lineHeight: 1.5,
              }}>
                {step.thinking}
              </div>
            )}
          </div>
        )}

        {/* sources */}
        {step.sources && step.sources.length > 0 && (
          <div style={{
            fontSize: 11,
            color: COLORS.success,
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            marginBottom: 2,
          }}>
            <FileTextOutlined style={{ fontSize: 10 }} />
            <span>检索到 {step.sources.length} 条内容</span>
          </div>
        )}

        {/* prompt */}
        {step.prompt && (
          <div style={{
            padding: '4px 8px',
            background: '#fffbe6',
            border: '1px solid #ffe58f',
            borderRadius: 4,
            fontSize: 11,
            color: '#d48806',
            marginBottom: 2,
          }}>
            <InfoCircleOutlined style={{ marginRight: 4 }} />
            {step.prompt}
          </div>
        )}

        {/* error */}
        {step.error && (
          <div style={{
            padding: '4px 8px',
            background: '#fff2f0',
            border: '1px solid #ffccc7',
            borderRadius: 4,
            fontSize: 11,
            color: COLORS.error,
            marginBottom: 2,
          }}>
            <CloseCircleOutlined style={{ marginRight: 4 }} />
            {step.error}
          </div>
        )}
      </div>
    </div>
  );
}

// ===== 主组件 =====

function ThinkingTimeline({ processMessages, isStreaming }) {
  const [expanded, setExpanded] = useState(false);

  // 流式时强制展开
  useEffect(() => {
    if (isStreaming) setExpanded(true);
  }, [isStreaming]);

  // 流式结束时自动折叠
  const prevStreamingRef = useState(isStreaming)[0];
  useEffect(() => {
    if (!isStreaming && prevStreamingRef) {
      setExpanded(false);
    }
  }, [isStreaming]); // eslint-disable-line react-hooks/exhaustive-deps

  const steps = useMemo(
    () => groupMessagesToSteps(processMessages || [], isStreaming),
    [processMessages, isStreaming]
  );

  if (steps.length === 0) return null;

  // 流式态：直接渲染时间线
  if (isStreaming) {
    return (
      <div style={{ marginBottom: 6, padding: '6px 0' }}>
        {steps.map((step, i) => (
          <StepItem key={step.id} step={step} isLast={i === steps.length - 1} />
        ))}
      </div>
    );
  }

  // 完成态：折叠摘要 / 展开时间线
  const summary = generateSummary(steps);

  return (
    <div style={{ marginBottom: 4 }}>
      {/* 摘要行 */}
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          padding: '5px 10px',
          background: COLORS.bgHover,
          borderRadius: 6,
          fontSize: 11,
          color: COLORS.textSecondary,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          userSelect: 'none',
          transition: 'background 0.15s',
        }}
        onMouseEnter={(e) => { e.currentTarget.style.background = COLORS.bgActive || '#e6f7ff'; }}
        onMouseLeave={(e) => { e.currentTarget.style.background = COLORS.bgHover; }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <SearchOutlined style={{ fontSize: 11 }} />
          {summary}
        </span>
        {expanded
          ? <UpOutlined style={{ fontSize: 9 }} />
          : <DownOutlined style={{ fontSize: 9 }} />}
      </div>

      {/* 展开时间线 */}
      {expanded && (
        <div style={{ padding: '6px 10px 2px 10px' }}>
          {steps.map((step, i) => (
            <StepItem key={step.id} step={step} isLast={i === steps.length - 1} />
          ))}
        </div>
      )}
    </div>
  );
}

export default ThinkingTimeline;
