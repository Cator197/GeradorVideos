document.addEventListener('DOMContentLoaded', () => {
  const toggleButton = document.getElementById('toggle-dark');
  const body = document.getElementById('app-body');

  // Aplica o tema salvo anteriormente, se houver
  const savedTheme = localStorage.getItem('theme');
  if (savedTheme === 'dark') {
    body.classList.add('dark');
    toggleButton.textContent = '☀️ Modo Claro';
  }

  toggleButton.addEventListener('click', () => {
    const isDark = body.classList.toggle('dark');

    if (isDark) {
      toggleButton.textContent = '☀️ Modo Claro';
      localStorage.setItem('theme', 'dark');
    } else {
      toggleButton.textContent = '🌙 Modo Escuro';
      localStorage.setItem('theme', 'light');
    }
  });
});
