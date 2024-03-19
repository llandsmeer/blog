---
layout: post
title:  "Overwrite an existing C/C++ function without LD_PRELOAD hacks"
date:   2019-06-25 01:20:00 +0100
categories: tech
comments: true
---

In a ~~failed~~ attempt to speed up CPython using a C++ extension,
I found myself looking for a solution to overwrite (monkey patch)
a function in the compiled C code.
On linux, this is normally possible with `LD_PRELOAD`,
which enables you to prepend a library in the dynamic linker search path.
When your program requests an external function like `malloc`, the dynamic linker
starts searching for it and hopefully finds it in your prepended library.
The program will then call that function instead of the version from say, `glibc`.
However, this was not a possibility here, as I wanted to do this from within
a python module, which are dynamically loaded *after* program startup.
If this were C++, you'd maybe be able to overwrite vtables in certain situations,
but CPython is written in C.

# Implementation

So I wrote this hack that overwrites a existing C function
with a function of choice. Linux/x86_64 only, but the technique
is transferable to other platforms.

```cpp
void monkey_patch(void * sym, void * jump_target, int offset=0) {
    static int PAGE_SIZE = 0;
    if (PAGE_SIZE == 0) PAGE_SIZE = getpagesize();
    void * page = (void*)((uintptr_t)sym & (uintptr_t)~(PAGE_SIZE-1));
    struct {
        unsigned char jmp_qword_ptr_rip[6];
        uint64_t addr;
    } __attribute__((packed)) asm_jmp_abs = {
        {0xff, 0x25, 0, 0, 0, 0}, (uint64_t)jump_target
    };
    mprotect(page, 2 * PAGE_SIZE, PROT_WRITE);
    void * target = (void*)((uintptr_t)sym + offset);
    memcpy(target, &asm_jmp_abs, sizeof asm_jmp_abs);
    mprotect(page, 2 * PAGE_SIZE, PROT_READ | PROT_EXEC);
}

void monkey_patch(const char * function, void * jump_target, int offset=0) {
    static void * handle = 0;
    if (handle == 0) handle = dlopen(0, RTLD_LAZY);
    void * sym = dlsym(handle, function);
    monkey_patch(sym, jump_target, offset);
}
```

Compile with `-ldl`. You'd use it like:

```cpp
#include <iostream>

void puts_wrapper(const char * s) {
    std::cout << "You called puts(\"" << s << "\")" << std::endl;
}

int main() {
    monkey_patch("puts", (void*)&puts_wrapper);
    puts("Hello, World!");
}

// output: You called puts("Hello, World!")
```

# How does it work?

It uses dlopen()/dlsym() to locate the address of the function.
If it is not a dynamically loaded symbol, passing the function address is also fine.
Next, since linux uses W^X (meaning a page can't be writable and executable at the
same time), mprotect() is used to make the function writable at the page boundary.
A small piece of machine code ([found on stack overflow][1])
that jumps to the target function without clobbering registers,
is then written at function entry.


```
ff 25 00 00 00 00           jmp qword ptr [rip]
xx xx xx xx xx xx xx xx     64 bit jump address
```

At first, this code didn't work for me because I was patching PyEval_EvalCode(),
which calls the code in my extension. After monkey patching the CPU would continue
executing inside PyEval_EvalCode() (+0x23), so I included an offset parameter which
allows you to set the overwrite point inside a function.

Feel free to use it as you want to use, but expect things to break :).

[1]: https://stackoverflow.com/a/53876008
