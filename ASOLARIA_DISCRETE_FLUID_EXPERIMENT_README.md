# Asolaria-informed discrete fluid: first 3D exact-arithmetic experiment

**Status:** Executed and reproducible proof-of-concept, **not** a reproduction of the Asolaria ASI-OS runtime, a demonstration of native ternary hardware, a physical simulation of molecular water, or a proof of the 3D Navier–Stokes Millennium problem.

## What was tested

Can a **finite discrete microdynamics** transport momentum between layers and produce fluid-like relaxation without implementing a continuum PDE or using floating-point numbers?

A D3Q27 lattice gas, with three spatial coordinates and 27 velocity vectors `c_i=(cx,cy,cz)` whose components are in `{-1,0,+1}`. Each site has 27 occupancy trits `n_i=0,1,2`. Values are stored as bytes by the C++ implementation, although the *mathematical occupancy alphabet* is ternary. This is conventional binary CPU emulation, **not** native ternary logic.

- Periodic cube: **24 × 18 × 12 = 5,184 cells**.
- Microscopic occupancy variables: **139,968 trits**.
- Local deterministic 4-channel collision gates: **288** distinct rule tables, each an involution; 32 gates applied per site and tick according to a reproducible schedule.
- Evolving dynamics: stream along the 27 velocity vectors and apply local collisions that preserve particle number, all three momentum components and squared velocity sum.
- Steps: **288** in collision-free and collision-enabled controls.
- Initial state: opposite bulk momentum biases in top and bottom halves; random occupancy drawn from fixed-seed integer generator.

### Exact mathematical update

Let `x` denote a cell, `i` a velocity direction and `t` a discrete tick. Collision outputs `n_i*(x,t) = C(n(x,t))`, then each occupancy moves to its neighboring cell:

```text
n_i(x + c_i, t + 1) = n_i*(x, t)

mass(x)      = sum_i n_i(x)
momentum(x)  = sum_i c_i n_i(x)
energy2(x)   = sum_i |c_i|^2 n_i(x)    (twice unit-mass kinetic energy)
```

Each local collision table groups all 81 possible 4-channel trit configurations by the five integer conserved quantities `(mass, px, py, pz, energy2)` and swaps neighboring configurations **within each class**. Every map is validated at construction for exact conservation and involutivity. This is a constructed toy collision system, not a learned or experimentally calibrated collision law.

The equivalent macroscopic fields are number density `rho=sum_i n_i`, momentum density `j=sum_i n_i c_i`, and **rational** bulk velocity `u=j/rho` for positive `rho`. No floating-point division is needed in the simulation.

### Measurements

```
GLOBAL|mass=139945|px=-243|py=57|pz=-86|kinetic_energy_x2=279840|initial_shear=31101
```

`shear_contrast = sum(momentum_x in lower half) - sum(momentum_x in upper half)` (with the coordinate half chosen to match the biased initial state). It is an **integer contrast measure**, not physical viscosity.

| Tick | Shear contrast, streaming alone | Shear contrast, with collisions |
|---:|---:|---:|
| 0 | 31,101 | 31,101 |
| 6 | 3,275 | 18,101 |
| 12 | 3,071 | 11,815 |
| 18 | 31,101 | 8,119 |
| 24 | 3,275 | 5,453 |
| 36 | 31,101 | 3,047 |
| 48 | 3,071 | 1,647 |
| 60 | 3,275 | 1,043 |
| 72 | 31,101 | 273 |
| 96 | 3,275 | -175 |
| 144 | 31,101 | 311 |
| 288 | 31,101 | -75 |

Streaming-alone microstates return *exactly* to their starting values after tick 72 due to the periodic lattice dimensions and discrete velocities. With collisions, the starting microstate does **not** return at tick 72, and the large-scale initial shear contrast has fallen by `(31101-273)/31101 = 30828/31101` at tick 72 (~99.1%). All checks of global mass, momentum, and squared-speed energy passed at every recorded checkpoint.

**Microscopic reversibility:** After 72 collision-enabled steps, undoing streaming and applying the local collision gates in reverse order for ticks 71 ... 0 restored **every one of the 139,968 occupancy trits exactly**. This illustrates that apparently dissipative coarse-grained dynamics can arise from invertible deterministic microdynamics. The shear still has finite-size fluctuations at later ticks and is not proven to obey a Newtonian viscosity law.

## Run

```bash
g++ -O3 -std=c++17 -Wall -Wextra -Werror asolaria_ternary_fluid_v1.cpp -o asolaria_ternary_fluid_v1
./asolaria_ternary_fluid_v1 asolaria_ternary_fluid_v1_results.csv
```

No floating-point operators, libraries, coefficients, or integrators are used in the model. The local collision schedule, seed, spatial size and sample checkpoints are pinned in source. The measured results came from the compiled program executed in the current conversation runtime.

## What this does and does not explain

**Supported in this experiment:** finite discrete dynamics can transport momentum, homogenize initial macroscopic shear, and conserve mass, momentum and energy exactly. Coarse-grained relaxation is not a demonstration of microscopic information loss; the dynamics have a tested inverse.

**Not established:** physical space is fundamentally discrete, real molecular collisions use this ternary collision table, the model has the correct pressure/viscosity/equation of state, Galilean invariance, isotropy to the required order, Navier–Stokes recovery, 3D turbulence statistics, experimentally measured fluid properties, black-hole singularity resolution, or a refutation of mathematical blowup. D3Q27 is a well-established discrete-velocity lattice; the rule table and this test are exploratory rather than evidence of a new fundamental theory.

## Concrete next scientific checks

1. **Hydrodynamic calibration:** start with weak sinusoidal shear (constructed with exact rational or fixed-point arithmetic), fit effective kinematic viscosity with integer residuals, and test grid-size stability.
2. **Rotational invariance:** repeat momentum perturbations along x/y/z and diagonal directions, compare relaxation rates and stress tensor components.
3. **Equation of state and sound:** measure equilibrium momentum flux, density-wave propagation and pressure response with finite sampling errors.
4. **Boundaries and forcing:** implement particle-solid bounceback; compare planar Poiseuille and Couette flows with reference measurements.
5. **Physical bridge:** identify physical units, molecular length/time/energy scales and transport coefficients; compare to dilute gas kinetic theory or molecular dynamics.
6. **Integrate with Asolaria:** introduce an adapter from the published 27-shell state and Q-PRISM readout to physical density/momentum/energy moments; verify whether mapping preserves quantities and whether changing local resolution modifies macroscopic predictions. Do not assume equivalence.

## Background references

- NASA Glenn Research Center, *Kinetic Theory of Gases* — molecular momentum transfer and macroscopic properties: https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/kinetic-theory-of-gasses/
- Frisch, Hasslacher & Pomeau, *Lattice-Gas Automata for the Navier-Stokes Equation*, Physical Review Letters 56, 1505 (1986): https://doi.org/10.1103/PhysRevLett.56.1505
- Karlin et al., *Extended Lattice Boltzmann Model*, Entropy 23(4), 475 (2021): https://pmc.ncbi.nlm.nih.gov/articles/PMC8073312/
- Doostmohammadi, *The Navier-Stokes equations blow up, and planes still fly*, Communications Physics 9, 325 (2026): https://doi.org/10.1038/s42005-026-02930-y
