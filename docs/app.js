function App() {
    const [city, setCity] = React.useState("");
    const [results, setResults] = React.useState("");
    const [error, setError] = React.useState("");

    const handleSearchCity = () => {
        if (!city.trim()) {
            setError("Por favor, introduce una ciudad.");
            setResults("");
            return;
        }

        setError("");
        setResults(`Buscando información para la ciudad: ${city}`);
    };

    return (
        <div>
            <h1>Búsqueda de Ciudad</h1>
            <label htmlFor="city-input">Introducir ciudad:</label>
            <input
                id="city-input"
                type="text"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                placeholder="Escribe tu ciudad..."
            />
            <button type="button" onClick={handleSearchCity}>
                Buscar ciudad
            </button>
            {error && <p style={{ color: "red" }}>{error}</p>}
            {results && <p>{results}</p>}
        </div>
    );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
