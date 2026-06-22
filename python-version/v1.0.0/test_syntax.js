
// 页面加载前先获取主题并应用，防止闪烁
(function() {
  var xhr = new XMLHttpRequest();
  xhr.open('GET', '/api/site/theme', false); // 同步请求
  try {
    xhr.send();
    var data = JSON.parse(xhr.responseText);
    var theme = data.theme || 'cyberpunk';
    if (theme !== 'cyberpunk') {
      document.documentElement.className = '';
      document.body.className = 'theme-' + theme;
    }
    window._initialTheme = theme;
  } catch(e) {
    window._initialTheme = 'cyberpunk';
  }
})();
