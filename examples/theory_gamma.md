## The gamma distribution

A gamma variable is the total of k independent exponential waiting times, each
with mean θ, so it models the time until the k-th event of a memoryless process.
Its support is the positive reals and its shape is right-skewed. A variable X
with shape k and scale θ has density

$$f(x) = \frac{1}{\theta^{k}\,\Gamma(k)}\; x^{k-1}\, e^{-x/\theta} \,, \qquad x > 0$$

The shape k sets how many waiting times are summed and the scale θ stretches the
axis. As k grows the sum of many exponentials becomes more symmetric and
approaches a normal density, the central limit theorem acting from inside the
family.

## Estimation

The first two moments give the parameters directly through

$$\mathrm{E}[X] = k\theta \,, \qquad \mathrm{Var}[X] = k\theta^{2}$$

so the method of moments inverts them into

$$\hat{k} = \frac{\bar{X}^{2}}{s^{2}} \,, \qquad
\hat{\theta} = \frac{s^{2}}{\bar{X}}$$

where X̄ is the sample mean and s² the sample variance. Unlike the normal family
the maximum-likelihood shape has no closed form and is found numerically, so the
method of moments is the quick estimate the analysis tab reports.

## What the simulation shows

The worker draws n independent gamma variates with numpy's `default_rng(seed)`,
so a given seed reproduces the sample. The **histogram** compares the draw
against its method-of-moments density, and the **fit** analysis recovers the
shape and scale from the sample moments. Scanning the shape sharpens the density
and pulls it toward symmetry as k rises, and scanning the scale stretches it
along the x axis without changing its form.
