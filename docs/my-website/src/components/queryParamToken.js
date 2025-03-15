import React, { useState, useEffect } from 'react';

const QueryParamToken = () => {
  const [token, setToken] = useState(null);

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    setToken(token);
  }, []);

  return (
    <span style={{ padding: 0, margin: 0 }}>
      {token ? <a href={`https://admin.llm.ai/${token}`} target="_blank" rel="noopener noreferrer">admin.llm.ai</a> : ""}
    </span>
  );
}

export default QueryParamToken;