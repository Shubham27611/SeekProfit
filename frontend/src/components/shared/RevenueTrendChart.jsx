import {
    ResponsiveContainer,
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
} from "recharts";
import { OVERVIEW } from "@/constants/testIds";

// Sample series shape only — no fake AI logic. This is a visual scaffold that
// will be wired to real financial data in Stage 2.
const DEFAULT_SERIES = [
    { m: "Jul", recovered: 42, potential: 68 },
    { m: "Aug", recovered: 51, potential: 74 },
    { m: "Sep", recovered: 63, potential: 79 },
    { m: "Oct", recovered: 58, potential: 82 },
    { m: "Nov", recovered: 71, potential: 88 },
    { m: "Dec", recovered: 84, potential: 96 },
    { m: "Jan", recovered: 92, potential: 104 },
    { m: "Feb", recovered: 108, potential: 118 },
];

const TooltipCard = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
        <div className="rounded-md border border-border bg-popover px-3 py-2 shadow-xl">
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                {label}
            </p>
            <div className="mt-1 space-y-0.5">
                {payload.map((p) => (
                    <div
                        key={p.dataKey}
                        className="flex items-center gap-2 font-mono text-xs"
                    >
                        <span
                            className="inline-block h-2 w-2 rounded-full"
                            style={{ background: p.color }}
                        />
                        <span className="capitalize text-muted-foreground">
                            {p.dataKey}
                        </span>
                        <span className="ml-auto tabular-nums text-foreground">
                            ${p.value}k
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
};

export const RevenueTrendChart = ({ data = DEFAULT_SERIES }) => {
    return (
        <div data-testid={OVERVIEW.chart} className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                    data={data}
                    margin={{ top: 8, right: 12, left: -12, bottom: 0 }}
                >
                    <defs>
                        <linearGradient
                            id="sp-area-recovered"
                            x1="0"
                            y1="0"
                            x2="0"
                            y2="1"
                        >
                            <stop
                                offset="0%"
                                stopColor="hsl(160 84% 39%)"
                                stopOpacity={0.35}
                            />
                            <stop
                                offset="100%"
                                stopColor="hsl(160 84% 39%)"
                                stopOpacity={0}
                            />
                        </linearGradient>
                        <linearGradient
                            id="sp-area-potential"
                            x1="0"
                            y1="0"
                            x2="0"
                            y2="1"
                        >
                            <stop
                                offset="0%"
                                stopColor="hsl(240 5% 65%)"
                                stopOpacity={0.18}
                            />
                            <stop
                                offset="100%"
                                stopColor="hsl(240 5% 65%)"
                                stopOpacity={0}
                            />
                        </linearGradient>
                    </defs>
                    <CartesianGrid
                        vertical={false}
                        stroke="hsl(240 4% 16%)"
                        strokeDasharray="2 6"
                    />
                    <XAxis
                        dataKey="m"
                        stroke="hsl(240 5% 45%)"
                        tickLine={false}
                        axisLine={false}
                        tick={{ fontSize: 11, fontFamily: "JetBrains Mono" }}
                    />
                    <YAxis
                        stroke="hsl(240 5% 45%)"
                        tickLine={false}
                        axisLine={false}
                        tick={{ fontSize: 11, fontFamily: "JetBrains Mono" }}
                        tickFormatter={(v) => `$${v}k`}
                        width={44}
                    />
                    <Tooltip
                        cursor={{
                            stroke: "hsl(240 4% 26%)",
                            strokeDasharray: "3 3",
                        }}
                        content={<TooltipCard />}
                    />
                    <Area
                        type="monotone"
                        dataKey="potential"
                        stroke="hsl(240 5% 55%)"
                        strokeWidth={1.25}
                        fill="url(#sp-area-potential)"
                    />
                    <Area
                        type="monotone"
                        dataKey="recovered"
                        stroke="hsl(160 84% 39%)"
                        strokeWidth={2}
                        fill="url(#sp-area-recovered)"
                    />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
};

export default RevenueTrendChart;
