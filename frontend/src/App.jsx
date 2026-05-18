import { useEffect, useState } from "react";
import "./App.css";

function App() {

  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {

    fetch("http://127.0.0.1:8000/products/")
      .then((res) => res.json())
      .then((data) => {
        setProducts(data.products);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });

  }, []);

  return (
    <div className="container">

      <h1>MundoMaterno</h1>

      <p>
        Inteligencia competitiva para ropa materna.
      </p>

      {loading ? (
        <p>Cargando productos...</p>
      ) : (
        <div className="grid">

          {products.map((product) => (

            <div className="card" key={product.id}>

              <h3>{product.name}</h3>

              <p>
                <strong>Competidor:</strong> {product.competitor}
              </p>

              <p>
                <strong>Categoría:</strong> {product.category}
              </p>

              <p>
                <strong>Precio:</strong> ${product.price}
              </p>

              {product.product_url && (
                <a
                  href={product.product_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  Ver producto
                </a>
              )}

            </div>

          ))}

        </div>
      )}

    </div>
  );
}

export default App;