function buildPoints(
    values,
    width,
    height,
    padding,
    minValue,
    maxValue
) {
    if (values.length === 0) {
        return [];
    }

    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;

    const range =
        maxValue === minValue
            ? 1
            : maxValue - minValue;

    return values.map((value, index) => {
        const x =
            values.length === 1
                ? width / 2
                : padding +
                  (index / (values.length - 1)) *
                      chartWidth;

        const y =
            height -
            padding -
            ((value - minValue) / range) *
                chartHeight;

        return {
            x,
            y,
            value,
        };
    });
}

function createPath(points) {
    if (points.length === 0) {
        return "";
    }

    return points
        .map((point, index) =>
            index === 0
                ? `M ${point.x} ${point.y}`
                : `L ${point.x} ${point.y}`
        )
        .join(" ");
}

function getNiceMax(value) {
    if (value <= 0) {
        return 1;
    }

    return Math.ceil(value / 5) * 5;
}

function HistoryChart({
    title,
    subtitle,
    values,
    labels,
    valueLabel,
    threshold = null,
}) {
    const width = 760;
    const height = 280;
    const padding = 40;

    if (!values || values.length === 0) {
        return (
            <div className="history-chart-card">
                <div className="history-chart-header">
                    <div>
                        <h4>{title}</h4>

                        {subtitle && (
                            <p>{subtitle}</p>
                        )}
                    </div>

                    <span className="history-chart-value-label">
                        {valueLabel}
                    </span>
                </div>

                <div className="history-chart-empty">
                    No historical data available.
                </div>
            </div>
        );
    }

    const numericValues = values.map(
        (value) => Number(value) || 0
    );

    const numericThreshold =
        threshold !== null &&
        threshold !== undefined
            ? Number(threshold)
            : null;

    const highestValue = Math.max(
        ...numericValues,
        numericThreshold ?? 0
    );

    const minValue = 0;
    const maxValue = getNiceMax(highestValue);

    const points = buildPoints(
        numericValues,
        width,
        height,
        padding,
        minValue,
        maxValue
    );

    const path = createPath(points);

    const gridLines = 4;

    let thresholdY = null;

    if (
        numericThreshold !== null &&
        Number.isFinite(numericThreshold) &&
        numericThreshold <= maxValue
    ) {
        const chartHeight = height - padding * 2;

        thresholdY =
            height -
            padding -
            ((numericThreshold - minValue) /
                (maxValue - minValue)) *
                chartHeight;
    }

    return (
        <div className="history-chart-card">
            <div className="history-chart-header">
                <div>
                    <h4>{title}</h4>

                    {subtitle && (
                        <p>{subtitle}</p>
                    )}
                </div>

                <div className="history-chart-meta">
                    {numericThreshold !== null && (
                        <span className="history-threshold-label">
                            Threshold:{" "}
                            {numericThreshold}
                        </span>
                    )}

                    <span className="history-chart-value-label">
                        {valueLabel}
                    </span>
                </div>
            </div>

            <div className="history-chart-wrapper">
                <svg
                    className="history-chart"
                    viewBox={`0 0 ${width} ${height}`}
                    role="img"
                    aria-label={title}
                >
                    {Array.from({
                        length: gridLines + 1,
                    }).map((_, index) => {
                        const y =
                            padding +
                            (index / gridLines) *
                                (height -
                                    padding * 2);

                        const value =
                            maxValue -
                            (index / gridLines) *
                                maxValue;

                        return (
                            <g key={index}>
                                <line
                                    x1={padding}
                                    y1={y}
                                    x2={
                                        width -
                                        padding
                                    }
                                    y2={y}
                                    className="history-chart-grid-line"
                                />

                                <text
                                    x={padding - 8}
                                    y={y + 4}
                                    textAnchor="end"
                                    className="history-chart-axis-label"
                                >
                                    {Math.round(
                                        value
                                    )}
                                </text>
                            </g>
                        );
                    })}

                    <line
                        x1={padding}
                        y1={height - padding}
                        x2={
                            width - padding
                        }
                        y2={
                            height - padding
                        }
                        className="history-chart-axis-line"
                    />

                    {thresholdY !== null && (
                        <>
                            <line
                                x1={padding}
                                y1={thresholdY}
                                x2={
                                    width -
                                    padding
                                }
                                y2={thresholdY}
                                className="history-threshold-line"
                            />

                            <text
                                x={
                                    width -
                                    padding
                                }
                                y={
                                    thresholdY - 7
                                }
                                textAnchor="end"
                                className="history-threshold-text"
                            >
                                Threshold{" "}
                                {
                                    numericThreshold
                                }
                            </text>
                        </>
                    )}

                    <path
                        d={path}
                        className="history-chart-line"
                    />

                    {points.map(
                        (point, index) => (
                            <circle
                                key={index}
                                cx={point.x}
                                cy={point.y}
                                r="4"
                                className="history-chart-point"
                            >
                                <title>
                                    {labels?.[
                                        index
                                    ] || "-"}{" "}
                                    —{" "}
                                    {point.value}{" "}
                                    people
                                </title>
                            </circle>
                        )
                    )}

                    {labels &&
                        labels.map(
                            (
                                label,
                                index
                            ) => {
                                if (
                                    labels.length >
                                        6 &&
                                    index %
                                            Math.ceil(
                                                labels.length /
                                                    6
                                            ) !==
                                        0 &&
                                    index !==
                                        labels.length -
                                            1
                                ) {
                                    return null;
                                }

                                const point =
                                    points[
                                        index
                                    ];

                                return (
                                    <text
                                        key={
                                            index
                                        }
                                        x={
                                            point.x
                                        }
                                        y={
                                            height -
                                            12
                                        }
                                        textAnchor="middle"
                                        className="history-chart-time-label"
                                    >
                                        {
                                            label
                                        }
                                    </text>
                                );
                            }
                        )}
                </svg>
            </div>
        </div>
    );
}

export function CrowdHistoryChart({
    history,
}) {
    const orderedHistory = [
        ...(history || []),
    ].reverse();

    const values = orderedHistory.map(
        (item) => item.total_people ?? 0
    );

    const labels = orderedHistory.map(
        (item) => {
            if (!item.result_timestamp) {
                return "-";
            }

            const date = new Date(
                item.result_timestamp
            );

            if (
                Number.isNaN(
                    date.getTime()
                )
            ) {
                return "-";
            }

            return date.toLocaleTimeString(
                [],
                {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                }
            );
        }
    );

    return (
        <HistoryChart
            title="Crowd Count Trend"
            subtitle="Recent whole-camera people count"
            values={values}
            labels={labels}
            valueLabel="People"
        />
    );
}

export function ZoneHistoryChart({
    zoneName,
    zoneId,
    history,
}) {
    const orderedHistory = [
        ...(history || []),
    ].reverse();

    const values = orderedHistory.map(
        (item) => item.count ?? 0
    );

    const labels = orderedHistory.map(
        (item) => {
            if (!item.result_timestamp) {
                return "-";
            }

            const date = new Date(
                item.result_timestamp
            );

            if (
                Number.isNaN(
                    date.getTime()
                )
            ) {
                return "-";
            }

            return date.toLocaleTimeString(
                [],
                {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                }
            );
        }
    );

    const threshold =
        orderedHistory.length > 0
            ? orderedHistory[
                  orderedHistory.length - 1
              ].threshold
            : null;

    return (
        <HistoryChart
            title={`${zoneName} Trend`}
            subtitle={`${zoneId} — recent zone count`}
            values={values}
            labels={labels}
            valueLabel="People"
            threshold={threshold}
        />
    );
}