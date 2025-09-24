// Admin inline totals for Journal lines (debit/credit)
(function(){
  function parseNum(v){ var n=parseFloat((v||"").replace(/,/g,"")); return isNaN(n)?0:n; }
  function computeTotals(){
    var wrap = document.querySelector("#journalline_set-group") || document.querySelector(".inline-group");
    if(!wrap) return;
    var debits  = wrap.querySelectorAll("input[name$='-debit']");
    var credits = wrap.querySelectorAll("input[name$='-credit']");
    var dr=0, cr=0;
    debits.forEach(function(inp){ dr += parseNum(inp.value); });
    credits.forEach(function(inp){ cr += parseNum(inp.value); });
    var diff = +(dr - cr).toFixed(2);

    var bar = document.getElementById("jl-totals-bar");
    if(!bar){
      bar = document.createElement("div");
      bar.id = "jl-totals-bar";
      bar.style.cssText = "margin:10px 0;padding:8px 12px;border:1px solid #ddd;background:#fafafa;display:flex;gap:24px;font-weight:600;";
      wrap.appendChild(bar);
    }
    bar.innerHTML = "Debit: " + dr.toFixed(2) + "  |  Credit: " + cr.toFixed(2) + "  |  Difference: " + diff.toFixed(2);
    // Highlight when balanced
    bar.style.borderColor = (Math.abs(diff) < 0.005) ? "#3fa63f" : "#d9534f";
  }

  function bind(){
    var wrap = document.querySelector("#journalline_set-group") || document.querySelector(".inline-group");
    if(!wrap) return;
    wrap.addEventListener("input", function(e){
      var n = e.target && e.target.name || "";
      if(n.endsWith("-debit") || n.endsWith("-credit")) computeTotals();
    });
    computeTotals();
  }

  if(document.readyState === "loading"){
    document.addEventListener("DOMContentLoaded", bind);
  }else{
    bind();
  }
})();
