document.getElementById("rideForm").addEventListener("submit", async function (e) {
    e.preventDefault();

    const data = {
        pickup_lat: parseFloat(document.getElementById("pickup_lat").value),
        pickup_lng: parseFloat(document.getElementById("pickup_lng").value),
        drop_lat: parseFloat(document.getElementById("drop_lat").value),
        drop_lng: parseFloat(document.getElementById("drop_lng").value),
        traffic_level: parseInt(document.getElementById("traffic_level").value)
    };

    const response = await fetch("http://127.0.0.1:8000/ride/quote", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    });

    const result = await response.json();

    document.getElementById("result").innerHTML = `
        ETA: ${result.eta.toFixed(2)} minutes <br>
        Estimated Cost: ₹${result.cost.toFixed(2)} <br>
        Demand Level: ${result.demand.toFixed(2)}
    `;
    

});
fetch("http://127.0.0.1:8000/ride/quote", {
    method: "POST",
    headers: {
        "Content-Type": "application/json"
    },
    body: JSON.stringify(data)
});

fetch("http://127.0.0.1:8000/ride/quote", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(data)
})
.then(res => {
    console.log("Status:", res.status);
    return res.json();
})
.then(result => {
    console.log("Result:", result);
})
.catch(err => {
    console.error("Fetch error:", err);
});


