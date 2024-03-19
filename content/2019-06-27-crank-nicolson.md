---
layout: post
title:  "Numerical solution of linear PDEs: Computing the Crank-Nicolson matrix automatically"
date:   2019-06-27 01:30:00 +0100
categories: tech
comments: true
---

The [Crank-Nicolson] method rewrites a discrete time
linear PDE as a matrix multiplication $$\phi_{n+1}=C \phi_n$$.
Nonlinear PDE's pose some additional
problems, but are solvable as well this way (by linearizing every timestep).
A major advantage here
is that going $$k$$ steps into the future is just $$\phi_{n+k}=C^{k}\phi_n$$,
and calculating a [matrix power] is polynomial time.
The method is in general very stable.

[matrix power]: https://docs.scipy.org/doc/numpy/reference/generated/numpy.linalg.matrix_power.html
[Crank-Nicolson]: https://en.wikipedia.org/wiki/Crank%E2%80%93Nicolson_method

For an assignment I had to construct the Crank-Nicolson
matrix for a simple linear 1 dimension PDE, which had to be derived by hand.
That's a bit labourus, so I made a method to derive it automatically.
As I came across it while sifting through some older files,
and could still not find that method elsewhere online,
I thought I might as well write it up here.

# Derivation (1D)

This is the standard Crank-Nicolson expression for a linear,
1 dimensional PDE. The time stepping matrix would then
be $$\mathbf{C}=\mathbf{A}^{-1}\mathbf{B}$$.

$$
\begin{align}
    \phi^{n+1} - \frac{\Delta t}2 f^{n+1} =& \; \phi^n +
        \frac{\Delta t}2 f^n =\\
    \mathbf{A} \phi^{n+1} =& \; \mathbf{B} \phi^n
\end{align}
$$

Since $$f$$ is linear, we can expand it into the set of its
impulse responses $$\left\{h^k\right\}$$. These are the vector outputs $$h^k =
f\left(\delta^k\right)$$ by applying it to a shifted unit impulse $$\delta^k_i =
\delta_{ik}$$. We can then rewrite $$f$$ in terms of its impulse responses:

$$
\begin{equation}
    f\left(\phi\right)_i = \sum_k h^k_i \phi_k
\end{equation}
$$

The Crank-Nicolson equation can be rewritten by substituting $$f$$ for
this definition with the goal of reformulating it as a matrix
equation.  Focusing on a single element $$\phi^{n+1}_i$$ and moving the
$$\phi^n$$ terms not resulting from $$f\left(\phi\right)$$ into the sum
one obtains

$$
\begin{equation}
    \sum_k  \delta_{ik} \phi^{n+1}_i - \frac{\Delta t}2 h^k_i \phi^{n+1}_k =
    \sum_k  \delta_{ik} \phi^n_i + \frac{\Delta t}2 h^k_i \phi^n_k
\end{equation}
$$

Equating this with the definition of the matrix-vector dot product \\
$$(\mathbf{A}\vec x)_i = \sum_k A_{ik} x_k$$
gives the elements of the Crank-Nicolson matrices $$\mathbf{A}$$ and $$\mathbf{B}$$:

$$
\begin{align}
    \mathbf{A}_{ik} = \delta_{ik} - \frac{\Delta t}2 h^k_i \\
    \mathbf{B}_{ik} = \delta_{ik} + \frac{\Delta t}2 h^k_i
\end{align}
$$

# Implementation

Here is a simple diffusion-advection example in Javascript.
Click to reset and apply new values.
<div id="cn_draw"></div>
Advection(1st derivative): <input type="number" value="-50" id="conf_cd1"/><br/>
Diffusion(2nd derivative): <input type="number" value="0.05" id="conf_cd2"/>

The implementation in Python is a straightforward translation of the
equations above. Note that `int(i == k)` is the Kronecker delta
$$\delta_{ik}$$.

```python
import numpy as np
import numpy.linalg as LA

def cn_lin_mat(f, n, dt):
    d = np.eye(n)                       # shifted impulses {delta^k}
    h = [f(di) for di in d]             # shifted impulse responses {h^k}
    A = np.zeros((n, n))
    B = np.zeros((n, n))
    for i in range(n):
        for k in range(1, n+1):
            k = k % n
            A[i, k] = int(i == k) - dt/2*h[k][i]
            B[i, k] = int(i == k) + dt/2*h[k][i]
    Ainv = LA.inv(A)
    C = Ainv @ B
    return C
```

# Higher Dimensions

This generalizes
trivially to higher dimensions.
You just have to rewrite f so that it works on 1 dimensional data,
by reshaping it at appriopiate times.
So, for a 2d linear PDE over a field with width `W` and height `H`
it would result in the following code. You'd probably want to use
sparse arrays for $$\mathbf{A}$$ and $$\mathbf{B}$$,
since they have $$(WH)^2$$ elements, of which most are 0.

```python
def f1d(phi):
    phi = phi.reshape((H, W))
    phi_next = f(phi)
    return phi_next.flatten()

C = cn_lin_mat(f1d, W*H, dt)
phi1 = (C @ phi0.flatten()).reshape((H, W))
```

<style>
    #cn_draw {
        display: block;
        height: 200px;
        width: 100%;
        background-color: #70c6d8;
    }

    .cn_bar {
        display: inline-block;
        height: 200px;
        width: 1%;
    }

    .cn_fill {
        display: block;
        width: 100%;
        background-color: white;
    }

    #cn_draw::nth-child(2) {
        background-color: green;
    }
</style>


<script src="/js/linalg.min.js"></script>

<script>
(function () {
    const DX = 0.01
    const DT = DX * DX
    const N = 100
    let conf_cd1 = 0.1
    let conf_cd2 = 0.1

    let elem_cd1 = document.getElementById('conf_cd1')
    let elem_cd2 = document.getElementById('conf_cd2')

    function shifted_impulse(n, i) {
        let z = new Array(n).fill(0)
        z[i] = 1
        return Matrix(z)
    }

    function roll(x, n) {
        let sz = x.rows
        let y = new Array(sz).fill(0)
        for (let i = 0; i < sz; i++) {
            let idx = (i - n) % sz
            while (idx < 0) idx += sz
            while (idx > sz) idx -= sz
            y[i] = x[idx]
        }
        return Matrix(y)
    }

    function cd1(x, dx) {
        let left = roll(x, +1)
        let right = roll(x, -1)
        let cd1 = Matrix.mul(right.sub(left), 1/(2*dx))
        return cd1
    }

    function cd2(x, dx) {
        let left = roll(x, 1)
        let right = roll(x, -1)
        let cd2 = Matrix.mul(right.sub(Matrix.mul(x, 2)).add(left), 1/(dx*dx))
        return cd2
    }

    function init(n) {
        conf_cd1 = parseFloat(elem_cd1.value)
        conf_cd2 = parseFloat(elem_cd2.value)
        let phi = Matrix(new Array(n).fill(0))
        for (let i = 0; i < N; i++) {
            let x = -Math.pow(i / N - 0.5, 2)*500
            phi[i] = Math.exp(x)
        }
        C = cn_lin_mat(f, N, DT)
        return phi
    }

    function f(phi) {
        let a = Matrix.mul(cd1(phi, DX), conf_cd1)
        if (conf_cd2 == 0) return a;
        let b = Matrix.mul(cd2(phi, DX), conf_cd2)
        return a.add(b)
    }

    function zeros(n) {
        let res = []
        for (let i = 0; i < n; i++) {
            res.push(new Array(n).fill(0))
        }
        return Matrix(res)
    }


    function cn_lin_mat(f, n, dt) {
        let h = []
        for (let i = 0; i < n; i++) {
            let d = shifted_impulse(n, i)
            let res = f(d)
            h.push(res)
        }
        let A = zeros(n)
        let B = zeros(n)
        for (let i = 0; i < n; i++) {
            for (let ki = 1; ki <= n; ki++) {
                const k = ki % n
                const delta_ik = i == k ? 1 : 0
                A[i*N+k] = delta_ik - dt/2*h[k][i]
                B[i*N+k] = delta_ik + dt/2*h[k][i]
            }
        }
        const Ainv = Matrix.invertLUP(A)
        const C = Matrix.mul(Ainv, B)
        return C
    }

    const fill = '<div class="cn_bar"><div class="cn_fill"></div></div>'
    let innerHTML = ''

    for (let i = 0; i < N; i++) {
        innerHTML = innerHTML + fill
    }

    let C = null
    let phi = init(N)
    let cn_draw = document.getElementById('cn_draw')

    cc = C

    cn_draw.innerHTML = innerHTML

    function step() {
        phi = Matrix.mul(C, phi)
        for (let i = 0; i < N; i++) {
            let bar = cn_draw.childNodes[i].childNodes[0]
            let x = phi[i]
            if (x > 1) x = 1
            if (x < 0) x = 0
            bar.style.height = (1-x)*200 + 'px'
        }
        setTimeout(step, 20)
    }

    setTimeout(step, 1)

    cn_draw.onclick = function() {
        phi = init(N)
        return false
    }
})()
</script>

