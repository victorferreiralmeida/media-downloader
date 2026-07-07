// URL da API usada pelo frontend.
// Em produção no GitHub Pages, aponta para a instância remota do backend.
const DEFAULT_API_BASE = "http://137.131.227.77:8000";

if (!window.API_BASE) {
  const { protocol, hostname, port, origin } = window.location;

  if (protocol === "file:") {
    window.API_BASE = "http://127.0.0.1:8000";
  } else if (
    (hostname === "127.0.0.1" || hostname === "localhost" || hostname === "[::1]") &&
    port === "8000"
  ) {
    window.API_BASE = origin;
  } else if (hostname === "127.0.0.1" || hostname === "localhost" || hostname === "[::1]") {
    window.API_BASE = "http://127.0.0.1:8000";
  } else if (hostname.endsWith(".github.io")) {
    window.API_BASE = DEFAULT_API_BASE;
  } else {
    window.API_BASE = DEFAULT_API_BASE;
  }
}
