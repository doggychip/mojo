'use client';

interface MiniChartProps {
  data: number[];
  positive?: boolean;
  width?: number;
  height?: number;
}

export default function MiniChart({ data, positive = true, width = 80, height = 32 }: MiniChartProps) {
  if (!data || data.length < 2) return null;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((v - min) / range) * height;
    return `${x},${y}`;
  });

  const color = positive ? '#22C55E' : '#EF4444';
  const fillColor = positive ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)';

  const pathD = `M ${points.join(' L ')}`;
  const lastPoint = points[points.length - 1];
  const firstPoint = `0,${height}`;
  const fillPathD = `M ${firstPoint} L ${points.join(' L ')} L ${lastPoint.split(',')[0]},${height} Z`;

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <path d={fillPathD} fill={fillColor} />
      <path d={pathD} stroke={color} strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
