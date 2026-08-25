import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";

export const metadata: Metadata = {
  title: "Methods",
  description: "Every equation, assumption and citation behind the Earth-2.0 analysis.",
};

function Eq({ children }: { children: React.ReactNode }) {
  return (
    <pre className="my-3 overflow-x-auto rounded-[var(--radius-md)] border border-[var(--color-line)] bg-[var(--color-panel)] px-4 py-3 font-[family-name:var(--font-mono)] text-[12.5px] leading-relaxed text-[var(--color-cyan)]">
      {children}
    </pre>
  );
}

export default function MethodsPage() {
  return (
    <>
      <PageHeader
        eyebrow="Method"
        title="Equations and methodology"
        lede="Every model implemented in this project, with its citation, its stated validity range, and the assumption it makes explicit rather than silent."
      />
      <div className="mx-auto max-w-[1400px] px-4 py-10 sm:px-6">
        <div className="prose-sci mx-auto">
          <h2 id="hz">Habitable-zone boundaries</h2>
          <p>
            Kopparapu, R. K. et al. (2013), <em>Habitable Zones Around
            Main-Sequence Stars: New Estimates</em>, ApJ 765, 131,
            doi:10.1088/0004-637X/765/2/131, with the corrected coefficients from
            the Erratum, ApJ 770, 82, doi:10.1088/0004-637X/770/1/82.
          </p>
          <Eq>{`S_eff = S_eff,sun + a·T + b·T² + c·T³ + d·T⁴
T = T_eff − 5780 K
valid for 2600 K ≤ T_eff ≤ 7200 K

d = √(L / S_eff)   [au], L in solar luminosities`}</Eq>
          <p>
            Five boundaries are computed (recent Venus, runaway greenhouse,
            moist greenhouse, maximum greenhouse, early Mars). The{" "}
            <strong>conservative</strong> habitable zone is runaway greenhouse
            to maximum greenhouse; the <strong>optimistic</strong> zone is
            recent Venus to early Mars. Outside the stated temperature range the
            model returns an explicit &ldquo;extrapolated&rdquo; flag rather
            than a silently clamped value.
          </p>

          <h2 id="esi">Earth Similarity Index</h2>
          <p>
            Schulze-Makuch, D. et al. (2011), <em>A Two-Tiered Approach to
            Assessing the Habitability of Exoplanets</em>, Astrobiology 11(10),
            1041–1052, doi:10.1089/ast.2010.0592.
          </p>
          <Eq>{`F_x = 1 − |(x − x₀) / (x + x₀)|

ESI_global = F_radius^(w_r/4) · F_density^(w_d/4)
           · F_escape_velocity^(w_v/4) · F_temperature^(w_t/4)

  w_r = 0.57, w_d = 1.07, w_v = 0.70, w_t = 5.58

Computed in two tiers for reporting (plain product within each
tier, since w/2 is already applied per term -- one combining
sqrt only, not a sqrt per tier):

ESI_interior = F_radius^(w_r/2) · F_density^(w_d/2)
ESI_surface  = F_escape_velocity^(w_v/2) · F_temperature^(w_t/2)
ESI_global   = √(ESI_interior · ESI_surface)`}</Eq>
          <p>
            The temperature term is referenced to Earth&rsquo;s{" "}
            <strong>equilibrium</strong> temperature (254 K), not its surface
            temperature (288 K), because equilibrium temperature is the only
            temperature exoplanet catalogues provide. Consequence: Venus scores
            0.92 on this metric. This is documented in{" "}
            <a href="/limitations" className="link">
              Limitations
            </a>
            .
          </p>

          <h2 id="mc">Monte Carlo uncertainty propagation</h2>
          <p>
            Every parameter with a published asymmetric uncertainty is sampled
            from a two-piece (split) normal: draw z ~ N(0,1), scale by the
            upper sigma when z &gt; 0 and the lower sigma when z &lt; 0.
            Non-positive draws on positive-definite quantities are rejected and
            redrawn (bounded attempts), never clipped to zero.
          </p>
          <Eq>{`x_sample = x + z·σ_upper   if z > 0
x_sample = x + z·σ_lower   if z ≤ 0

4,000 draws per planet, seed fixed for reproducibility`}</Eq>

          <h2 id="rocky">Rocky plausibility</h2>
          <p>
            Rogers, L. A. (2015), <em>Most 1.6 Earth-Radius Planets are not
            Rocky</em>, ApJ 801, 41, doi:10.1088/0004-637X/801/1/41; Fulton, B.
            J. et al. (2017), <em>The California-Kepler Survey III</em>, AJ 154,
            109 (the radius-valley result).
          </p>
          <Eq>{`p(rocky) = 1 / (1 + exp((R_p − 1.6) / 0.20))`}</Eq>
          <p>
            A logistic centred on 1.6 R⊕, spanning the observed 1.5–2.0 R⊕
            radius valley, rather than a hard cut the data does not support.
          </p>

          <h2 id="tsm">Characterisation metrics</h2>
          <p>
            Kempton, E. M.-R. et al. (2018), <em>A Framework for Prioritizing
            the TESS Planetary Candidates Most Amenable to Atmospheric
            Characterization</em>, PASP 130, 114401, doi:10.1088/1538-3873/aadf6f.
          </p>
          <Eq>{`TSM = S · (R_p³ · T_eq) / (M_p · R_star²) · 10^(−m_J/5)
S = 0.190 / 1.26 / 1.28 / 1.15  by radius bin (<1.5 / 1.5–2.75 / 2.75–4.0 / >4.0 R⊕)

ESM = 4.29×10⁶ · (B₇.₅(T_day) / B₇.₅(T_star)) · (R_p/R_star)² · 10^(−m_K/5)`}</Eq>

          <h2 id="composite">Composite Earth-2.0 index</h2>
          <Eq>{`index = exp( Σᵢ wᵢ · log(max(scoreᵢ, ε)) ),  Σwᵢ = 1,  ε = 0.01

Default weights: similarity 0.35, habitability 0.40,
                 confidence 0.25, characterisation 0.0`}</Eq>
          <p>
            A weighted <strong>geometric</strong> mean, chosen specifically
            because it is non-compensatory: a near-zero component drags the
            whole index toward zero regardless of how strong the others are.
          </p>

          <h2 id="rv-eq">Radial-velocity semi-amplitude and minimum mass</h2>
          <Eq>{`K = 28.4329 m/s · (Mp sin i / M_Jup) · ((M* + Mp)/M_sun)^(−2/3)
                              · (P / 1 yr)^(−1/3) / √(1 − e²)`}</Eq>
          <p>
            Inverted to recover M sin i from a fitted K. Reported only when a
            fit passes a three-criterion reliability gate: at least 20
            velocities, amplitude significance ≥3σ, and residual scatter below
            five times the fitted amplitude.
          </p>

          <h2 id="constants">Physical constants</h2>
          <p>
            IAU 2015 Resolution B3 nominal solar and terrestrial conversion
            constants; CODATA 2018 fundamental constants. Full values in{" "}
            <code>src/earth2/constants.py</code> in the repository, each with
            its source.
          </p>
        </div>
      </div>
    </>
  );
}
