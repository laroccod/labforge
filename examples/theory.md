## The normal distribution

Sums of independent, finite-variance perturbations converge to the normal
distribution regardless of the perturbations' own law. It is the fixed point of
the central limit theorem, which is why it appears wherever many small effects
aggregate. A variable X with mean μ and standard deviation σ has density

$$f(x) = \frac{1}{\sigma\sqrt{2\pi}}\; e^{-(x-\mu)^2 / 2\sigma^2}$$

The family is closed under affine maps. Standardizing any member,

$$Z = \frac{X - \mu}{\sigma} \sim \mathcal{N}(0,\, 1)$$

shows that μ only translates the density and σ only stretches it, so every
member of the family is the same law seen through a location-scale
transformation.

## Estimation

The two parameters are exactly the first two moments, E[X] = μ and
Var[X] = σ². Their maximum-likelihood estimators are the sample analogues

$$\hat{\mu} = \frac{1}{n}\sum_{i=1}^{n} X_i \,, \qquad
\hat{\sigma}^2 = \frac{1}{n}\sum_{i=1}^{n} \left(X_i - \hat{\mu}\right)^2$$

so the method of moments and maximum likelihood coincide here, a special
property of this family rather than a general fact. Applying the central limit
theorem to the estimator itself gives the familiar √n error bar

$$\sqrt{n}\,\left(\hat{\mu} - \mu\right) \sim \mathcal{N}(0,\, \sigma^2)
\qquad \mathrm{as}\;\; n \to \infty$$

## What the simulation shows

The worker draws n independent variates with numpy's `default_rng(seed)`, so a
given seed always reproduces the same sample. The **histogram** compares the
draw against its fitted density. The **Q-Q plot** compares the standardized
order statistics against standard-normal quantiles, where a Gaussian sample
lies on the diagonal. Scanning μ or σ runs the draw once per point of the
cartesian grid. The overlaid histograms and the per-row moments table then
make the location-scale structure of the family directly visible.
