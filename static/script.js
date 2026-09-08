let priceChart = null;


// =====================================================
// PREDICT STOCK
// =====================================================

async function predictStock() {

    const input =
        document.getElementById("tickerInput").value.trim();

    if (!input) {

        showError("Please enter a stock ticker.");

        return;

    }


    showLoading();

    hideError();

    hideDashboard();


    try {

        const tickers = input
            .split(",")
            .map(t => t.trim())
            .filter(t => t.length > 0);


        // =================================================
        // MULTIPLE STOCKS
        // =================================================

        if (tickers.length > 1) {

            await predictMultiple(tickers);

            return;

        }


        // =================================================
        // SINGLE STOCK
        // =================================================

        const ticker =
            encodeURIComponent(tickers[0]);


        const response =
            await fetch(`/predict?ticker=${ticker}`);


        const result =
            await response.json();


        if (!result.success) {

            throw new Error(result.error);

        }


        displayResult(result.data);

    }

    catch (error) {

        showError(
            error.message ||
            "Something went wrong."
        );

    }

    finally {

        hideLoading();

    }

}


// =====================================================
// DISPLAY SINGLE RESULT
// =====================================================

function displayResult(data) {

    showDashboard();


    // Prediction

    const prediction =
        document.getElementById("prediction");

    const signal =
        document.getElementById("signal");


    if (data.prediction === "UP") {

        prediction.innerHTML =
            "🔼 UP";

        prediction.style.color =
            "#22c55e";

        signal.innerHTML =
            "BUY";

        signal.style.background =
            "rgba(34,197,94,0.15)";

        signal.style.color =
            "#4ade80";

    }

    else {

        prediction.innerHTML =
            "🔽 DOWN";

        prediction.style.color =
            "#ef4444";

        signal.innerHTML =
            "SELL";

        signal.style.background =
            "rgba(239,68,68,0.15)";

        signal.style.color =
            "#f87171";

    }


    // Price

    document.getElementById("price")
        .innerText =
        "$" + data.current_price.toLocaleString();


    // RSI

    document.getElementById("rsi")
        .innerText =
        data.rsi;


    // MA5

    document.getElementById("ma5")
        .innerText =
        data.ma5;


    // MA10

    document.getElementById("ma10")
        .innerText =
        data.ma10;


    // Volatility

    document.getElementById("volatility")
        .innerText =
        data.volatility + "%";


    // Confidence

    const confidence =
        data.confidence;


    document.getElementById("confidence")
        .innerText =
        confidence + "%";


    updateConfidence(confidence);


    // Chart

    createChart(data.chart);

}


// =====================================================
// CONFIDENCE CIRCLE
// =====================================================

function updateConfidence(value) {

    const circle =
        document.getElementById(
            "confidenceCircle"
        );


    const degrees =
        value * 3.6;


    circle.style.background =
        `conic-gradient(
            #22c55e ${degrees}deg,
            #1f2937 ${degrees}deg
        )`;

}


// =====================================================
// CHART
// =====================================================

function createChart(data) {

    const ctx =
        document.getElementById(
            "priceChart"
        );


    if (priceChart) {

        priceChart.destroy();

    }


    const labels =
        data.map(item => item.date);


    const prices =
        data.map(item => item.price);


    priceChart =
        new Chart(ctx, {

            type: "line",

            data: {

                labels: labels,

                datasets: [

                    {

                        label: "Price",

                        data: prices,

                        borderWidth: 2,

                        pointRadius: 0,

                        tension: 0.3

                    }

                ]

            },

            options: {

                responsive: true,

                maintainAspectRatio: false,

                plugins: {

                    legend: {

                        display: false

                    }

                },

                scales: {

                    x: {

                        ticks: {

                            color: "#9ca3af",

                            maxTicksLimit: 10

                        },

                        grid: {

                            display: false

                        }

                    },

                    y: {

                        ticks: {

                            color: "#9ca3af"

                        },

                        grid: {

                            color:
                                "rgba(255,255,255,0.06)"

                        }

                    }

                }

            }

        });

}


// =====================================================
// MULTIPLE STOCKS
// =====================================================

async function predictMultiple(tickers) {

    try {

        const query =
            encodeURIComponent(
                tickers.join(",")
            );


        const response =
            await fetch(
                `/predict-multiple?tickers=${query}`
            );


        const result =
            await response.json();


        if (!result.success) {

            throw new Error(
                result.error
            );

        }


        showDashboard();


        document
            .getElementById(
                "multiStockSection"
            )
            .classList.remove("hidden");


        const table =
            document.getElementById(
                "stockTable"
            );


        table.innerHTML = "";


        result.data.forEach(stock => {

            const row =
                document.createElement("tr");


            let predictionClass =
                stock.prediction === "UP"
                    ? "up"
                    : "down";


            row.innerHTML = `

                <td>
                    <strong>
                        ${stock.ticker}
                    </strong>
                </td>

                <td class="${predictionClass}">
                    ${
                        stock.prediction === "UP"
                        ? "🔼 UP"
                        : "🔽 DOWN"
                    }
                </td>

                <td>
                    ${stock.signal}
                </td>

                <td>
                    ${stock.confidence}%
                </td>

                <td>
                    $${stock.current_price}
                </td>

            `;


            table.appendChild(row);

        });

    }

    catch (error) {

        showError(
            error.message
        );

    }

    finally {

        hideLoading();

    }

}


// =====================================================
// UI HELPERS
// =====================================================

function showLoading() {

    document
        .getElementById("loading")
        .classList.remove("hidden");

}


function hideLoading() {

    document
        .getElementById("loading")
        .classList.add("hidden");

}


function showDashboard() {

    document
        .getElementById("dashboard")
        .classList.remove("hidden");

}


function hideDashboard() {

    document
        .getElementById("dashboard")
        .classList.add("hidden");

}


function showError(message) {

    const error =
        document.getElementById("error");

    error.innerText =
        "⚠️ " + message;

    error.classList.remove("hidden");

}


function hideError() {

    document
        .getElementById("error")
        .classList.add("hidden");

}


// =====================================================
// ENTER KEY
// =====================================================

document
    .getElementById("tickerInput")
    .addEventListener(
        "keypress",
        function(event) {

            if (event.key === "Enter") {

                predictStock();

            }

        }
    );