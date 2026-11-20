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
  formatRate,
  type GroupReport,
} from '@/lib/api/reports-types';

interface GroupChartProps {
  groups: GroupReport[];
  caption: string;
}

const WIDTH = 640;
const LABEL_WIDTH = 160;
const BAR_WIDTH = 420;
const ROW_HEIGHT = 62;

function shortName(value: string): string {
  return value.length > 24 ? `${value.slice(0, 23)}…` : value;
}

export function GroupChart({ groups, caption }: GroupChartProps) {
  if (groups.length === 0) {
    return null;
  }
  const height = groups.length * ROW_HEIGHT + 10;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
        <span className="inline-flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-sm bg-primary" aria-hidden="true" />
          {en.reports.clickRateColumn}
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-sm bg-success" aria-hidden="true" />
          {en.reports.reportRateColumn}
        </span>
      </div>
      <svg
        viewBox={`0 0 ${WIDTH} ${height}`}
        role="img"
        aria-label={en.reports.groupsTitle}
        className="h-auto w-full"
      >
        {groups.map((group, index) => {
          const top = index * ROW_HEIGHT + 8;
          const clickWidth = Math.max(0, Math.min(1, group.click_rate)) * BAR_WIDTH;
          const reportWidth = Math.max(0, Math.min(1, group.report_rate)) * BAR_WIDTH;
          return (
            <g key={group.id}>
              <text
                x="0"
                y={top + 14}
                className="fill-current text-xs font-semibold text-foreground"
              >
                {shortName(group.name)}
              </text>
              <text
                x="0"
                y={top + 30}
                className="fill-current text-[10px] text-muted-foreground"
              >
                {group.department ?? en.reports.noDepartment}
              </text>
              <rect
                x={LABEL_WIDTH}
                y={top + 4}
                width={BAR_WIDTH}
                height="10"
                rx="5"
                className="fill-current text-surface-muted"
              />
              <rect
                x={LABEL_WIDTH}
                y={top + 19}
                width={BAR_WIDTH}
                height="10"
                rx="5"
                className="fill-current text-surface-muted"
              />
              <rect
                x={LABEL_WIDTH}
                y={top + 4}
                width={clickWidth}
                height="10"
                rx="5"
                className="chart-bar fill-current text-primary"
              >
                <title>{`${group.name}: ${en.reports.clickRateColumn} ${formatRate(group.click_rate)}`}</title>
              </rect>
              <rect
                x={LABEL_WIDTH}
                y={top + 19}
                width={reportWidth}
                height="10"
                rx="5"
                className="chart-bar fill-current text-success"
              >
                <title>{`${group.name}: ${en.reports.reportRateColumn} ${formatRate(group.report_rate)}`}</title>
              </rect>
            </g>
          );
        })}
      </svg>

      <Table>
        <TableCaption>{caption}</TableCaption>
        <TableHeader>
          <TableRow>
            <TableHead scope="col">{en.reports.groupColumn}</TableHead>
            <TableHead scope="col">{en.reports.departmentColumn}</TableHead>
            <TableHead scope="col">{en.reports.delivered}</TableHead>
            <TableHead scope="col">{en.reports.clickRateColumn}</TableHead>
            <TableHead scope="col">{en.reports.reportRateColumn}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {groups.map((group) => (
            <TableRow key={group.id}>
              <TableCell>{group.name}</TableCell>
              <TableCell>{group.department ?? en.reports.noDepartment}</TableCell>
              <TableCell>{group.delivered}</TableCell>
              <TableCell>{formatRate(group.click_rate)}</TableCell>
              <TableCell>{formatRate(group.report_rate)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
