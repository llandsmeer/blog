---
layout: post
title:  "Matrix-multiplication for JAX PyTrees"
date:   2024-04-19 00:00:00 +0100
categories: tech
status: draft
---

JAX, in a way, is a extension over numpy which can handle python objects
like dicts, lists or custom classes, which it calles PyTrees.

Even better, it supports autograd through these PyTrees.
However, how to handle the resulting objects can sometimes be confusing (at least for me),
especially if you try to perform 'matrix multiplication'-type operations on PyTrees.

However


## Making it JIT-able

The PyTree definition objects sadly can not pass as static arguments for the JIT compiler,
so we have to make them available in the function scope in a different way:

```python
def make_pytree_matmul(
        ndef: jax.tree_util.PyTreeDef,
        kdef: jax.tree_util.PyTreeDef,
        mdef: jax.tree_util.PyTreeDef,
        kshape = None # if None assume only floats
        ):
    @jax.jit
    def pytree_matmul(
            A, # A(n, k)
            B # B(k, m)
            ):
        # matmul: c_ij = sum_k a_ik b_kj
        out = []
        for A_i_ in ndef.flatten_up_to(A): # i rows of A
            row = [0] * mdef.num_leaves
            for k, (A_ik, B_k_) in enumerate(zip(kdef.flatten_up_to(A_i_), kdef.flatten_up_to(B))): # k cols of A and rows of B
                for j, B_kj in enumerate(mdef.flatten_up_to(B_k_)): # j cols of B
                    if kshape is None or kshape[k] == ():
                        if isinstance(A_ik, jax.Array):
                            # print('SKIP!', A_ik.shape, B_kj.shape, k) 
                            pass  
                        else:
                            row[j] += A_ik * B_kj
                    else:
                        def prod(*x):
                            if not x:
                                return 1
                            return x[0] * prod(*x[1:])
                        ks = kshape[k]
                        ns = A_ik.shape[:-len(ks)]
                        ms = B_kj.shape[len(ks):]
                        o = A_ik.reshape(prod(*ns), prod(*ks)) @ B_kj.reshape(prod(*ks), prod(*ms))
                        row[j] += o.reshape(*ns, *ms)
            row = mdef.unflatten(row)
            out.append(row)
        out = ndef.unflatten(out)
        return out
    return pytree_matmul
```

## Addition

```python
@jax.jit
def pytree_add(a, b):
    def add(a, b): 
        return a + b
    return jax.tree_util.tree_map(add, a, b)
```
