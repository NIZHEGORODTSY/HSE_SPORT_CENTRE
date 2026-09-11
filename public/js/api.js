const Api = (() => {
  function initData() {
    return (window.Telegram && Telegram.WebApp && Telegram.WebApp.initData) || "";
  }

  async function request(method, path, body) {
    const res = await fetch(path, {
      method,
      headers: {
        "Content-Type": "application/json",
        "X-Telegram-Init-Data": initData(),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

    let data = null;
    try {
      data = await res.json();
    } catch (e) {
      data = null;
    }

    if (!res.ok) {
      const message = (data && data.detail) || `Ошибка ${res.status}`;
      throw new Error(message);
    }
    return data;
  }

  return {
    get: (path) => request("GET", path),
    post: (path, body) => request("POST", path, body),
    put: (path, body) => request("PUT", path, body),
    del: (path) => request("DELETE", path),
  };
})();
