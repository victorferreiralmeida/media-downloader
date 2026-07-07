// GitHub Pages: defina a URL da sua API antes do deploy, por exemplo:
// window.API_BASE = "https://api.seudominio.com";

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
  } else {
    window.API_BASE = origin;
  }
}
