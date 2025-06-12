document.addEventListener("DOMContentLoaded", function(){
  const btn = document.getElementById("btn-toggle-sidebar");
  const sidebar = document.getElementById("sidebar");
  btn.addEventListener("click", () => {
    sidebar.classList.toggle("collapsed");
  });
});
