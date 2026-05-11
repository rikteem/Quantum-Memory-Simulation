"""
Theory / README tab — displays the EIT background text in a scrollable pane.
The text is rendered as rich HTML so equations look typeset (Unicode math symbols).
"""

from __future__ import annotations
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextBrowser, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


THEORY_HTML = """
<html>
<head>
<style>
  body  { background:#1e1e2e; color:#cdd6f4; font-family:'Segoe UI',sans-serif; font-size:13px; margin:20px; }
  h1    { color:#cba6f7; border-bottom:1px solid #45475a; padding-bottom:6px; }
  h2    { color:#89b4fa; margin-top:20px; }
  h3    { color:#a6e3a1; }
  code  { background:#313244; color:#f38ba8; padding:2px 6px; border-radius:3px; font-family:Consolas,monospace; }
  .eq   { background:#181825; border-left:3px solid #89b4fa; padding:8px 16px;
          margin:10px 0; font-family:Consolas,monospace; font-size:13px; color:#cdd6f4; }
  .ref  { color:#6c7086; font-size:11px; }
  table { border-collapse:collapse; width:100%; }
  th    { background:#313244; color:#cba6f7; padding:6px 10px; text-align:left; }
  td    { padding:5px 10px; border-bottom:1px solid #45475a; }
  .warn { color:#f9e2af; }
</style>
</head>
<body>

<h1>&#955;-System EIT Quantum Memory</h1>

<h2>1. What is Quantum Memory?</h2>
<p>A <b>quantum memory</b> is a device that can coherently store and retrieve the quantum state
of a photon (or a pulse of light) using an atomic medium.  Unlike a classical buffer,
a quantum memory must preserve <em>phase coherence</em> and, ideally, operate at the
single-photon level.  Key figures of merit are:</p>
<ul>
  <li><b>Storage efficiency &#951;</b> — fraction of input photon energy retrieved.</li>
  <li><b>Storage time &#964;_s</b> — how long the state survives before decoherence.</li>
  <li><b>Fidelity F</b> — overlap between stored and retrieved quantum states.</li>
  <li><b>Multimode capacity</b> — number of independent temporal / spectral modes storable simultaneously.</li>
  <li><b>Bandwidth</b> — spectral acceptance window of the memory.</li>
</ul>

<h2>2. The &#916; (Lambda) System</h2>
<p>EIT quantum memory uses atoms with a <b>&#955;-level structure</b>:</p>
<ul>
  <li><code>|g&#10217;</code> — ground state (stable, coupled to signal photon)</li>
  <li><code>|e&#10217;</code> — excited state (decays at rate &#947;_e)</li>
  <li><code>|s&#10217;</code> — metastable ground state (spin-wave storage level, dephasing &#947;_s)</li>
</ul>
<p>A weak <b>signal field</b> E drives <code>|g&#10217; &#8594; |e&#10217;</code>.
A strong classical <b>control field</b> &#937; drives <code>|s&#10217; &#8594; |e&#10217;</code>.</p>

<h2>3. Electromagnetically Induced Transparency (EIT)</h2>
<p>When both fields are resonant (two-photon resonance, &#948; = 0), quantum interference between
excitation pathways creates a <em>transparency window</em> in an otherwise absorbing medium.
The medium becomes transparent to the signal — but at a dramatically <b>reduced group velocity</b>:</p>
<div class="eq">
  v_g = c &#183; &#937;&#178; / (&#937;&#178; + g&#178;N)
</div>
<p>where <b>g</b> is the single-atom coupling and <b>N</b> is the atom number.
In the limit &#937;&#178; &#8810; g&#178;N (high optical depth), v_g &#8810; c — the pulse is dramatically slowed.</p>

<h2>4. Storage and Retrieval</h2>
<p>The storage protocol works in three stages:</p>
<ol>
  <li><b>Write</b>: signal pulse enters medium while &#937; is on. The pulse slows to v_g, compressing inside the ensemble.</li>
  <li><b>Store</b>: &#937; is switched off adiabatically. The photon state maps onto a collective
    <em>spin-wave excitation</em> S(z) — a coherent superposition of atomic ground states.</li>
  <li><b>Retrieve</b>: &#937; is switched back on. The spin wave re-emits into the signal mode.</li>
</ol>
<p class="warn">&#9888; The adiabaticity condition requires |d&#937;/dt| &#8810; &#937;&#178;/&#947;_e.</p>

<h2>5. Maxwell-Bloch Equations</h2>
<p>The coupled evolution of the signal field E, optical coherence P &#8733; &#961;_ge,
and spin-wave S &#8733; &#961;_gs is governed by:</p>
<div class="eq">
  (&#8706;_t + c&#8706;_z) E = i&#183;g&#8730;N &#183; P
</div>
<div class="eq">
  &#8706;_t P = &minus;(&#947;_eg &minus; i&#916;&#8321;) P + i&#183;g&#8730;N &#183; E + i&#937; &#183; S
</div>
<div class="eq">
  &#8706;_t S = &minus;(&#947;_sg &minus; i&#948;) S + i&#937;* &#183; P
</div>
<p>where:</p>
<table>
  <tr><th>Symbol</th><th>Meaning</th></tr>
  <tr><td><code>&#947;_eg</code></td><td>Half-linewidth of optical transition = (&#947;_decay + &#947;_dephase_e)/2</td></tr>
  <tr><td><code>&#947;_sg</code></td><td>Ground-state decoherence rate = &#947;_dephase_s/2</td></tr>
  <tr><td><code>&#916;&#8321;</code></td><td>One-photon detuning of signal from <code>|g&#10217;&#8594;|e&#10217;</code></td></tr>
  <tr><td><code>&#948;</code></td><td>Two-photon (Raman) detuning &#916;&#8321; &minus; &#916;&#8322;</td></tr>
  <tr><td><code>g</code></td><td>Single-atom vacuum coupling constant</td></tr>
  <tr><td><code>N</code></td><td>Total atom number in the ensemble</td></tr>
</table>

<h2>6. Optical Depth (OD)</h2>
<p>The key figure of merit for EIT memory is the resonant optical depth:</p>
<div class="eq">
  OD = g&#178;&#183;N&#183;L / (c&#183;&#947;_eg)
</div>
<p>Storage efficiency scales approximately as:</p>
<div class="eq">
  &#951; &#8776; (1 &minus; 1/OD)&#178;
</div>
<p>High OD requires either many atoms (dense vapour) or a long ensemble.
Practical values OD &gt; 10 give &#951; &gt; 80%.</p>

<h2>7. EIT Bandwidth</h2>
<p>The transparency window has a half-width:</p>
<div class="eq">
  &#916;&#969;_EIT &#8776; &#937;&#178; / (&#947;_eg &#183; &#8730;OD)
</div>
<p>The signal pulse bandwidth must fit within this window for efficient storage.</p>

<h2>8. Numerical Implementation</h2>
<p>This simulator uses:</p>
<ul>
  <li><b>Slow-light approximation</b>: field equation uses v_g instead of c, reducing the
    required spatial resolution by c/v_g &#8250; 1.</li>
  <li><b>RK4 time integration</b> (4th-order Runge-Kutta).</li>
  <li><b>4th-order centred finite differences</b> for &#8706;_z E.</li>
  <li><b>Numba JIT</b> compilation for C-speed loops.</li>
</ul>
<div class="eq">
  CFL condition: dt &#8804; dz / c
</div>

<h2>9. Key Parameters and Physical Intuition</h2>
<table>
  <tr><th>Increase…</th><th>Effect</th></tr>
  <tr><td>N (atom number)</td><td>&#8593; OD, &#8593; &#951;, &#8595; v_g (slower pulse)</td></tr>
  <tr><td>g (coupling)</td><td>&#8593; OD, &#8593; &#951;, wider EIT bandwidth</td></tr>
  <tr><td>&#937; (control Rabi)</td><td>&#8593; v_g (faster), &#8593; EIT bandwidth, &#8595; &#951; if too fast (non-adiabatic)</td></tr>
  <tr><td>&#947;_sg (dephasing)</td><td>&#8595; storage time, &#8595; &#951;</td></tr>
  <tr><td>&#916;&#8321; (one-photon detuning)</td><td>Shifts EIT window, reduced absorption but also reduced coupling</td></tr>
  <tr><td>L (medium length)</td><td>&#8593; OD linearly, &#8593; &#951;</td></tr>
</table>

<h2>10. Common Atomic Systems</h2>
<table>
  <tr><th>Atom</th><th>Transition</th><th>&#955; (nm)</th><th>&#947;/(2&#960;) (MHz)</th><th>Typical medium</th></tr>
  <tr><td>Rb-87</td><td>D1 line</td><td>795</td><td>5.75</td><td>Vapour cell, MOT</td></tr>
  <tr><td>Rb-87</td><td>D2 line</td><td>780</td><td>6.07</td><td>Vapour cell, MOT</td></tr>
  <tr><td>Cs-133</td><td>D1 line</td><td>894</td><td>4.56</td><td>Vapour cell</td></tr>
  <tr><td>Pr:YSO</td><td>&#8319;H&#8324;&#8594;&#179;P&#8321;</td><td>606</td><td>0.0015</td><td>Solid-state crystal</td></tr>
  <tr><td>Nd:YVO&#8324;</td><td>&#8319;I&#8329;/&#8322;&#8594;&#8309;F&#8323;/&#8322;</td><td>1064</td><td>0.08</td><td>Solid-state crystal</td></tr>
</table>

<h2>11. Other Quantum Memory Protocols</h2>
<ul>
  <li><b>AFC (Atomic Frequency Comb)</b> — spectral grating in inhomogeneous absorption;
    multimode capacity; on-demand retrieval via control field. <em>Coming soon.</em></li>
  <li><b>GEM (Gradient Echo Memory)</b> — reversible inhomogeneous broadening via
    magnetic/Stark gradient; on-demand recall; high multimode capacity. <em>Coming soon.</em></li>
  <li><b>DLCZ protocol</b> — heralded single-photon storage via spontaneous Raman scattering.</li>
  <li><b>Photon echo (CRIB)</b> — controlled reversible inhomogeneous broadening.</li>
</ul>

<h2>12. References</h2>
<p class="ref">
[1] Gorshkov, A. V. et al., <em>Universal approach to optimal photon storage in atomic media</em>,
    PRL 98, 123601 (2007).<br>
[2] Fleischhauer, M. &amp; Lukin, M. D., <em>Dark-state polaritons in electromagnetically induced transparency</em>,
    PRL 84, 5094 (2000).<br>
[3] Hammerer, K., S&#248;rensen, A. S. &amp; Polzik, E. S., <em>Quantum interfaces between light and atomic ensembles</em>,
    Rev. Mod. Phys. 82, 1041 (2010).<br>
[4] Lukin, M. D., <em>Colloquium: Trapping and manipulating photon states in atomic ensembles</em>,
    Rev. Mod. Phys. 75, 457 (2003).<br>
[5] Simon, C. et al., <em>Quantum memories — a review based on the European Integrated Project
    Qubit Applications</em>, Eur. Phys. J. D 58, 1 (2010).
</p>

</body>
</html>
"""


class TheoryTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        browser = QTextBrowser()
        browser.setHtml(THEORY_HTML)
        browser.setFont(QFont("Segoe UI", 10))
        browser.setOpenExternalLinks(True)
        layout.addWidget(browser)
