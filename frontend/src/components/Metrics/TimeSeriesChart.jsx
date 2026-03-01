/**
 * 通用时序图表组件
 * 基于 recharts 封装，支持多指标折线/面积图
 */
import React, { useMemo } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { COLORS } from '../../styles/tokens';

// 预设调色板
const CHART_COLORS = [
  '#667eea', '#722ed1', '#13c2c2', '#52c41a',
  '#fa8c16', '#f5222d', '#eb2f96', '#1890ff',
];

/**
 * 将时序数据点转为 recharts 格式
 * @param {Array} dataPoints - 后端返回的 data_points
 * @param {Array} series - 系列定义 [{key, label, extract}]
 *   extract: (dataPoint) => number  从数据点提取值
 */
function transformData(dataPoints, series) {
  return dataPoints.map((dp) => {
    const row = { time: dp.timestamp * 1000 }; // ms for Date
    for (const s of series) {
      row[s.key] = s.extract(dp);
    }
    return row;
  });
}

/**
 * 格式化时间轴标签
 */
function formatTime(ts) {
  const d = new Date(ts);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

/**
 * 格式化 tooltip 时间
 */
function formatTooltipTime(ts) {
  const d = new Date(ts);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`;
}

/**
 * TimeSeriesChart 通用时序图表
 *
 * Props:
 * - dataPoints: 后端时序数据点数组 [{timestamp, counters, histograms}]
 * - series: 系列定义 [{key, label, extract, color?}]
 * - height: 图表高度 (默认 240)
 * - unit: Y 轴单位后缀 (如 "ms", "次")
 * - areaMode: 是否使用面积图 (默认 true)
 */
export function TimeSeriesChart({
  dataPoints = [],
  series = [],
  height = 240,
  unit = '',
  areaMode = true,
}) {
  const chartData = useMemo(
    () => transformData(dataPoints, series),
    [dataPoints, series]
  );

  if (chartData.length === 0) {
    return (
      <div style={{
        height,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: COLORS.textTertiary,
        fontSize: 13,
      }}>
        暂无时序数据，系统运行后将自动采集
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={chartData} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={COLORS.borderLight} />
        <XAxis
          dataKey="time"
          tickFormatter={formatTime}
          stroke={COLORS.textTertiary}
          fontSize={11}
          tickLine={false}
        />
        <YAxis
          stroke={COLORS.textTertiary}
          fontSize={11}
          tickLine={false}
          axisLine={false}
          unit={unit ? ` ${unit}` : ''}
        />
        <Tooltip
          labelFormatter={formatTooltipTime}
          contentStyle={{
            background: COLORS.bgCard,
            border: `1px solid ${COLORS.border}`,
            borderRadius: 6,
            fontSize: 12,
          }}
          formatter={(value) => [
            typeof value === 'number' ? value.toFixed(2) : value,
            undefined,
          ]}
        />
        <Legend
          wrapperStyle={{ fontSize: 12, paddingTop: 4 }}
        />
        {series.map((s, i) => {
          const color = s.color || CHART_COLORS[i % CHART_COLORS.length];
          return areaMode ? (
            <Area
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.label}
              stroke={color}
              fill={color}
              fillOpacity={0.1}
              strokeWidth={1.5}
              dot={false}
              activeDot={{ r: 3 }}
            />
          ) : (
            <Area
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.label}
              stroke={color}
              fill="none"
              strokeWidth={1.5}
              dot={false}
              activeDot={{ r: 3 }}
            />
          );
        })}
      </AreaChart>
    </ResponsiveContainer>
  );
}

export default TimeSeriesChart;
