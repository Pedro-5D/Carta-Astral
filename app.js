const App = () => {
    const [cityName, setCityName] = React.useState(""); // Correctamente inicializado
    const [results, setResults] = React.useState([]);
    const [error, setError] = React.useState(null);

    const handleSearch = async () => {
        try {
            setError(null);
            const response = await fetch(`/buscar_ciudad?nombre=${encodeURIComponent(cityName)}`);
            if (!response.ok) {
                throw new Error("Error al buscar ciudades");
            }
            const data = await response.json();
            setResults(data);
        } catch (err) {
            setError(err.message);
        }
    };

    return (
        <div>
            <div className="form-container">
                <label htmlFor="city-input">Introduce el nombre de la ciudad:</label>
                <input
                    id="city-input"
                    type="text"
                    value={cityName}
                    onChange={(e) => setCityName(e.target.value)}
                    placeholder="Ejemplo: Madrid"
                />
                <button onClick={handleSearch}>Buscar</button>
            </div>
            {error && <div className="error-message">{error}</div>}
            <div className="results-container">
                {results.length > 0 ? (
                    results.map((city, index) => (
                        <div key={index} className="result-item">
                            {city.name} - {city.country} (GMT Offset: {city.gmt_offset})
                        </div>
                    ))
                ) : (
                    <div>No hay resultados</div>
                )}
            </div>
        </div>
    );
};

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
