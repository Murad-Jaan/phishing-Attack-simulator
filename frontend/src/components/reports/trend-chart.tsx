import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { en } from '@/content/en';
import {
  formatDay,
  formatRate,
  type TrendPoint,
} from '@/lib/api/reports-types';

interface TrendChartProps {
  points: TrendPoint[];
  title: string;
  caption: string;
}

const WIDTH = 640;
const HEIGHT = 210;
const PADDING = { top: 18, right: 18, bottom: 34, left: 38 };

export function TrendChart({ points, title, caption }: TrendChartProps) {
  if (points.length === 0) {
    return null;
  }
  const plotWidth = WIDTH - PADDING.left - PADDING.right;
  const plotHeight = HEIGHT - PADDING.top - PADDING.bottom;
  const x = (index: number) =>
    points.length === 1
      ? PADDING.left + plotWidth / 2
      : PADDING.left + (index / (points.length - 1)) * plotWidth;
  const y = (rate: number) =>
    PADDING.top + (1 - Math.min(1, Math.max(0, rate))) * plotHeight;
  const polyline = points
    .map((point, index) => `${x(index)},${y(point.click_rate)}`)
    .join(' ');
  const first = points[0];
  const last = points[points.length - 1];

  return (
    <div className="space-y-4">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label={title}
        className="h-auto w-full"
      >
        {[0, 0.5, 1].map((rate) => (
          <g key={rate}>
            <line
              x1={PADDING.left}
              x2={WIDTH - PADDING.right}
              y1={y(rate)}
              y2={y(rate)}
              strokeWidth="1"
              className="stroke-current text-border"
            />
            <text
              x={PADDING.left - 8}
              y={y(rate) + 4}
              textAnchor="end"
              className="fill-current text-[10px] text-muted-foreground"
            >
              {formatRate(rate)}
            </text>
          </g>
        ))}
        <polyline
          points={polyline}
          fill="none"
          strokeWidth="3"
          strokeLinejoin="round"
          strokeLinecap="round"
          className="stroke-current text-primary"
        />
        {points.map((point, index) => (
          <circle
            key={point.date}
            cx={x(index)}
            cy={y(point.click_rate)}
            r="4"
            className="fill-current text-primary"
          >
            <title>{`${formatDay(point.date)}: ${formatRate(point.click_rate)}`}</title>
          </circle>
        ))}
        <text
          x={x(0)}
          y={HEIGHT - 10}
          textAnchor="middle"
          className="fill-current text-[10px] text-muted-foreground"
        >
          {formatDay(first.date)}
        </text>
        {points.length > 1 ? (
          <text
            x={x(points.length - 1)}
            y={HEIGHT - 10}
            textAnchor="middle"
            className="fill-current text-[10px] text-muted-foreground"
          >
            {formatDay(last.date)}
          </text>
        ) : null}
      </svg>

      <Table>
        <TableCaption>{caption}</TableCaption>
        <TableHeader>
          <TableRow>
            <TableHead scope="col">{en.reports.dateColumn}</TableHead>
            <TableHead scope="col">{en.reports.delivered}</TableHead>
            <TableHead scope="col">{en.reports.clicked}</TableHead>
            <TableHead scope="col">{en.reports.clickRateColumn}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {points.map((point) => (
            <TableRow key={point.date}>
              <TableCell>{formatDay(point.date)}</TableCell>
              <TableCell>{point.delivered}</TableCell>
              <TableCell>{point.clicked}</TableCell>
              <TableCell>{formatRate(point.click_rate)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
