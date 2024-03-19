---
layout: post
title:  "Building an UEFI x64 kernel from scratch: A long trip to userspace"
date:   2019-07-21 12:00:00 +0100
categories: tech
comments: true
---

When I just started programming, one of my first major projects was building my own kernel.
Of course, I failed misserably. But I learned a lot.
Back then, x64 didn't dominate the market and I never even heard about UEFI.
Copy pasting code bits from tutorials and forum posts I ended up
drawing some things to the screen based on keyboard input.
However, I never managed to get to userspace (/userland/CPL 3).

Things have changed a bit, and
I decided to finally write a 'modern' UEFI x64 kernel which is able to get to userspace, and document my
progress.
In kernel development, nothing is easy, and found myself repeatedly in painful late night debugging sessions
chasing strange kernel bugs.
I cut a few corners short, and found some nice tricks
to hack you way throught the standards in ways you shouldn't do,
but in the end, I finally got my kernel in functioning state in userspace.

For me, the most important lesson was maybe,
that copy pasting bits from the internet
will not help too much when building a kernel.
You just have to read the Intel manuals really
carefully. Luckily, they are quite readable.

This post is just to get you started, as figuring
the right way to configure your GDT or setting up
a minimal identity mapping can be very boring.
I hope someone can learn something from it :)

# Sysret

With the x86_64 architecture, a new faster method to
switch between kernel and userspace was added: the
`syscall`/`sysret` instructions. `syscall`
jumps from userspace to the kernel, and then the kernel
returns to userspace using `sysret`.
While this is a lot easier to program for than syscalls via interrupts,
a lot of work needs to be done before we can use them.

To quote the Intel Instruction Set Reference, N-Z, Vol. 2B 4-469, SYSRET:

> Upon return, SYSRET copies the value saved in RCX to the RIP.
> 
> In a return to 64-bit mode using Osize 64, SYSRET sets the CS selector value to MSR
> IA32_STAR[63:48] +16. The SS is set to IA32_STAR[63:48] + 8.

So we need a GDT with the correct segments in correct order and load that into the STAR
model specific register (MSR).
Furthermore, a paging setup that allows userspace code executablion.
For paging, we could pre allocate all page structures, but the Correct Way&trade; is to
have a page allocator do that dynamically for us. And for a page allocator,
we need to know which memory is available, by using the UEFI API.

# Development Setup

There are good instruction on
[the osdev wiki][osdev_uefi] on setting up a minimal UEFI x64 application
(the osdev wiki in general is an invaluable resource).
They use linux and GNU-EFI.
Depending on your setup, Tianocore EDK II might be more suitable.
In that case the UEFI calls change [a bit][uefi-grub-calling] (no initialization of globals,
`BS` becomes `gBS` and no uefi_call_wrapper()).
Littered around the internet numerous instructions can be found on how to set up the development
environment so I won't include it here.
The intel style assembly code included in this post was taken from a global
`asm("..\n...")` block in the C code with `-masm=intel` GCC flag.
Anyway, the kernel code here should work regardless of the development setup.
A minimal UEFI application looks like this:

```c
#include <efi.h>
#include <efilib.h>

EFI_STATUS
EFIAPI
efi_main(EFI_HANDLE ImageHandle, EFI_SYSTEM_TABLE *SystemTable) {
    InitializeLib(ImageHandle, SystemTable);
    return EFI_SUCCESS;
}
```

[osdev_uefi]: https://wiki.osdev.org/UEFI_Bare_Bones

# Debugging your UEFI OS Loader

You're free to do this in whatever way you want, but here is how I did it.

Debugging a kernel is hard. That's also what makes it a fun challenge, most of the time :).
For an UEFI OS loader this is even a bit harder, as we're not left in a
simple VGA text mode where we can write characters to a known memory location.
Instead we have to use the UEFI Console Services.
However, quite early, after loading our own GDT this is not supported anymore
and we're left in the dark.
By leaving code and data segments that correspond to the ones that
are expected by OVMF (the UEFI implementation I use) in qemu and not exiting boot services, you can still access them in a very hackish way.
You can find those segments by reading the `CS` and `DS` registers, eg. by a triple fault
with the `-d cpu_reset` qemu flag.

Then, qemu allows for the attachment of gdb with `-S -gdb tcp::9000`.
Fire up gdb and type `target remote localhost:9000`.
I didn't use that.
The `-no-reboot -no-shutdown` qemu flags are good for debugging triple faults,
by stopping it from going into a reboot loop.
With `-d int,cpu_reset` you get very verbose information on interupts and cpu resets.

The method I found most useful was downloading the qemu sourcecode and patching
it with logging statements when exceptions occurred.
This gives you access to the complete internal CPU state which is extremely useful.

```sh
$ git clone 'https://github.com/qemu/qemu/' qemu
$ cd qemu
$ ./configure
$ make x86_64-softmmu/all
# your qemu executable is now in qemu/x86_64-softmmu/qemu-system-x86_64
```

The files/functions I ended up patching were:

 -  **target/i386/excp_helper.c**: At a triple fault check_exception(),
    raise_exception_err_ra() or its variants will be called.
    An attempt at adding backtrace's failed, so I ended up looking up the exception
    numbers in `target/i386/cpu.h` (search for `#define EXCP??_*`) and the grepping
    the qemu codebase for calls to the function in excp_helper.c with the right
    exception #define as argument.
    During setting up paging, logging handle_mmu_fault() was really useful
    to see how the CPU performed the page walk. Adding a condition statement
    like `if (env->regs[R_R15] == 0xdeadbeef)` and loading R15 with 0xdeadbeef on kernel start
    helps to reduce noise. handle_mmu_fault() is called on every table fill,
    an error only occurs when it executes a `goto fault`.
 -  **target/i386/seg_helper.cs**: this is where most exceptions originate from.
    Just adding a simple printf() with the current `__LINE__` and `__FUNCTION__`
    before every call to a raise_exception_err_ra() functions helps enormously.
 -  **target/i386/misc_helper.c**: I wanted to be sure that I wrote the right values
    to model specific registers and added logging to helper_wrmsr().
    Later, I also added a new fake MSR such that the wrmsr instruction could be used to
    print integer values from the kernel (
    `if ((uint32_t)env->regs[R_ECX] == 0xdeadbeef) { printf("RDI=%ld(%lx) RSI=%ld(%lx) RDX=%ld(%lx)\n", ...`).
 -  **cpu.h**: when issueing a `sysret` to go to userspace, 
    the inlined function cpu_x86_load_seg_cache() gets called from helper_sysret() in `seg_helper.c`,
    which changes the cpu privilege level.
    Here you can log the new CPL, or just check `env->hflags & HF_CPL_MASK` afterwards
    (that function gets called *a lot*, and its defined in a header so you have to recompile
    quite some files).

# The Memory Map and Page Allocator

Taking control of the machine in a correct way, by getting a memory map and
calling `EFI_BOOT_SERVICES.ExitBootServices()` was actually the last thing implemented.
Technically, it should happen before everything else, so I decided to write this down first.
The reason we need a memory map is that we need a very minimal page allocator to set up paging to go to userspace.
And for a page allocator, we need to know where the free memory is at.

The quick 'n easy way is to load the UEFI shell (press escape in the OVMF waiting screen),
type `memmap -b` and look for the largest
free blob of available memory. For me, that was 0x1300000. Now, your page allocator
can just use that address, and bump it by a single page on each page allocation:


```c
uint64_t next_alloc_page = 0x1300000;
void * alloc_page() {
    void * page = (void*)next_alloc_page;
    next_alloc_page += 4096;
    return page;
}
```

Of course, that's not portable at all, and the correct way is to
read the UEFI memory map. If you just want to move on fast,
skip the next part. Reference the [UEFI Spec][uefi-spec]
*Memory Allocation Services* for details and [this][uefi-grub-calling] for why
uefi_call_wrapper() is needed (it is to fix calling conventions).
By calling `BS->GetMemoryMap()`, we ask the uefi firmware
to fill a buffer with `struct uefi_mmap` entries, where each entry
describes a memory region. As this struct might change between
versions, it contains a `desc_size` field with the struct size,
so our code will still work when a new field is added.
Note that the buffer size is in bytes, not the amount of memory map entries you want.

[uefi-spec]: https://uefi.org/specifications

[uefi-grub-calling]: https://www.rodsbooks.com/efi-programming/efi_services.html

```c
#define UEFI_MMAP_SIZE 0x4000
struct uefi_mmap {
    uint64_t nbytes;
    uint8_t buffer[UEFI_MMAP_SIZE];
    uint64_t mapkey;
    uint64_t desc_size;
    uint32_t desc_version;
} uefi_mmap;
void setup_uefi(EFI_HANDLE ImageHandle) {
    /* call GetMemoryMap(size, buffer, mapkey, desc_size, desc_version) */
    uefi_mmap.nbytes = UEFI_MMAP_SIZE;
    uefi_call_wrapper(BS->GetMemoryMap, 5,
            &uefi_mmap.nbytes,
            uefi_mmap.buffer,
            &uefi_mmap.mapkey,
            &uefi_mmap.desc_size,
            &uefi_mmap.desc_version);
    /* find largest continuous chunk of EfiConventionalMemory */
    uint64_t best_alloc_start = 0;
    uint64_t best_number_of_pages = 0;
    for (int i = 0; i < uefi_mmap.nbytes; i += uefi_mmap.desc_size) {
        EFI_MEMORY_DESCRIPTOR * desc = (EFI_MEMORY_DESCRIPTOR*)&uefi_mmap.buffer[i];
        if (desc->Type != EfiConventionalMemory) continue;
        if (desc->NumberOfPages > best_number_of_pages) {
            best_number_of_pages = desc->NumberOfPages;
            best_alloc_start = desc->PhysicalStart;
        }
    }
    next_alloc_page = best_alloc_start;
    /* call ExitBootServices(ImageHandle, mapkey) */
    uefi_call_wrapper(BS->ExitBootServices, 2,
            ImageHandle,
            uefi_mmap.mapkey);
    /* we are in control of the memory map now :) */
}
```

This is still far from a perfect page allocator,
as it is impossible to free pages and doesn't make use of
other available memory regions.
However, it works more than good enough to identity map all 128MB
of default qemu memory in 4kb pages (66 pages) :).
Maybe just preallocating a few pages in `.data`
would have been easier..

# Clearing Interrupts

Interrupts handling is not needed to go to userspace, so just disable interrupts.

```c
asm("cli");
```

# Setting up the GDT and TSS

Contrary to going to userspace, there are somehow tons of tutorials on how to load a GDT
or what it is, so I won't go in too much details.
In short, every GDT (global descriptor table) entry (descriptor) defines a `segment`,
which was used before paging to implement memory protection.
Each segment has attributes like its start (base), length (limit) and various bitflag settings.
In 64-bit, all segments overlap and span the entire address space so we can ignore the limit and base attributes.
The main focus lies on the GDT type flags, which define whether it is a code or data segment and set the privilege level.
By loading the segment registers with indices into the GDT, the cpu switches to the corresponding
privilege level.
Code segments go in the code segment register `CS`, and data segments go into the data segment registers
(`DS`, `ES`, `FS`, `GS`, `SS`).
It's a bit more complicated than it should be, but thats the way it works.

Then, there is also the Task State Segment (TSS).
It holds information on where execution should continue after an interrupt.
We're not handling those¸ but we're forced to have a segment descriptor telling where our TSS is in the GDT.

For `syscall`/`sysret`, we need a 64 bit GDT with data and code segments for both kernel and userspace.
While UEFI leaves us with a functional GDT, we technically don't know what it looks like so we need to define our own
one.

This is what I ended up with:

```c
#pragma pack (1)

struct gdt_entry {
  uint16_t limit15_0;            uint16_t base15_0;
  uint8_t  base23_16;            uint8_t  type;
  uint8_t  limit19_16_and_flags; uint8_t  base31_24;
};

struct tss {
    uint32_t reserved0; uint64_t rsp0;      uint64_t rsp1;
    uint64_t rsp2;      uint64_t reserved1; uint64_t ist1;
    uint64_t ist2;      uint64_t ist3;      uint64_t ist4;
    uint64_t ist5;      uint64_t ist6;      uint64_t ist7;
    uint64_t reserved2; uint16_t reserved3; uint16_t iopb_offset;
} tss;

__attribute__((aligned(4096)))
struct {
  struct gdt_entry null;
  struct gdt_entry kernel_code;
  struct gdt_entry kernel_data;
  struct gdt_entry null2;
  struct gdt_entry user_data;
  struct gdt_entry user_code;
  struct gdt_entry ovmf_data;
  struct gdt_entry ovmf_code;
  struct gdt_entry tss_low;
  struct gdt_entry tss_high;
} gdt_table = {
    {0, 0, 0, 0x00, 0x00, 0},  /* 0x00 null  */
    {0, 0, 0, 0x9a, 0xa0, 0},  /* 0x08 kernel code (kernel base selector) */
    {0, 0, 0, 0x92, 0xa0, 0},  /* 0x10 kernel data */
    {0, 0, 0, 0x00, 0x00, 0},  /* 0x18 null (user base selector) */
    {0, 0, 0, 0x92, 0xa0, 0},  /* 0x20 user data */
    {0, 0, 0, 0x9a, 0xa0, 0},  /* 0x28 user code */
    {0, 0, 0, 0x92, 0xa0, 0},  /* 0x30 ovmf data */
    {0, 0, 0, 0x9a, 0xa0, 0},  /* 0x38 ovmf code */
    {0, 0, 0, 0x89, 0xa0, 0},  /* 0x40 tss low */
    {0, 0, 0, 0x00, 0x00, 0},  /* 0x48 tss high */
};

#pragma pack ()

```

Nothing special.
Our user base selector will be 0x18, the value we'll load into the STAR MSR high bits.
On `sysret`, `CS` will be set to 0x18+16=0x28 and `SS` to 0x18+8=0x20.
That are the correct segment indices we set up for user code and user data.

Note how there are two descriptors for the TSS. This is needed to store
a full 64 bit pointer to the TSS base (the higher half goes in the second TSS descriptor's limit).
Not that we need that because qemu has only 128Mb memory by default,
but otherwise qemu will give you an exception.

There are two segments for the OVMF firmware.
Calling into the UEFI Console Services results in an exception, but I found that adding segments
at the offsets 0x30 (data) and 0x38 (code) makes it possible to call them again.
After that your cpu state is most likely broken beyond repair, but it is sometimes useful to see
wheter a certain piece of code gets executed. You shouldn't make too much use of it probably.

Next, we need to put the TSS address into the GDT as its impossible to let the linker figure that out.
We are then ready to load the GDT using the `lgdt` instruction and set up the segment registers
with our newly defined segments.
The most important change here from most 'load the GDT and jump to long mode' tutorial code, is
that I replaced the `far jump` with a `lretq`.
While you should use a far jump to load a 64 bit GDT in protected (32 bit) mode, this instruction
is not supported in 64 bit mode itself (?!) and you have to resort to something like `lretq`.
See section *7.2.3 TSS Descriptor in 64-bit mode* of the *Intel 64 and IA-32 Architectures Software Developer's Manuel
for a more detailed explanation of the TSS entry layout.

```c
#pragma pack (1)

struct table_ptr {
    uint16_t limit;
    uint64_t base;
};

#pragma pack ()

extern /* defined in assembly */
void load_gdt(struct table_ptr * gdt_ptr);

void * memzero(void * s, uint64_t n) {
    for (int i = 0; i < n; i++) ((uint8_t*)s)[i] = 0;
}

void setup_gdt() {
    memzero((void*)&tss, sizeof(tss));
    uint64_t tss_base = ((uint64_t)&tss);
    gdt_table.tss_low.base15_0 = tss_base & 0xffff;
    gdt_table.tss_low.base23_16 = (tss_base >> 16) & 0xff;
    gdt_table.tss_low.base31_24 = (tss_base >> 24) & 0xff;
    gdt_table.tss_low.limit15_0 = sizeof(tss);
    gdt_table.tss_high.limit15_0 = (tss_base >> 32) & 0xffff;
    gdt_table.tss_high.base15_0 = (tss_base >> 48) & 0xffff;

    struct table_ptr gdt_ptr = { sizeof(gdt_table)-1, (UINT64)&gdt_table };
    load_gdt(&gdt_ptr);
}
```

The actual GDT loading assembly code:

```
.global load_gdt
load_gdt:
    lgdt [rdi]      ; load GDT, rdi (1st argument) contains the gdt_ptr
    mov ax, 0x40    ; TSS segment is 0x40
    ltr ax          ; load TSS
    mov ax, 0x10    ; kernel data segment is 0x10
    mov ds, ax      ; load kernel data segment in data segment registers
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov ss, ax
    popq rdi        ; pop the return address
    mov rax, 0x08   ; kernel code segment is 0x08
    pushq rax       ; push the kernel code segment
    pushq rdi       ; push the return address again
    lretq           ; do a far return, like a normal return but
                    ; pop an extra argument of the stack
                    ; and load it into CS
```

That should get you a nice and functioning GDT.

# Setting up Paging

Paging is mandatory in x86_64.
All regular memory accesses go through the MMU,
which translates the *virtual address*
into a *physical address*.
At the same time, access control is applied like readable/writable, user accessible etc..
In this way, the kernel can hide its own and other processes
memory contents from the current executing process, or enable sharing of a piece of memory
between processes.
All memory locations seen in userspace are actually virtual addresses.

This translation is defined in a hierachy of mapping tables.
In 64 bit mode (IA-32E paging), there a 4 levels of mapping tables:
Page map level 4 (PML4), page directory pointer table (PDPT),
page directory (PD) and the page table (PT).
Each mapping table spans 1 page (4096 bytes) in size and contains 512 8-byte entries.
There is only one PML4, which refers to up to 512 PDPTs. These in turn point to
up to $$2^{18}$$ page directories, which point to up to $$2^{27}$$ page tables.
Page tables entries contain the the physical addresses of the page they
refer to, so in total the PML4 spans
a maximum of $$4096\cdot2^{4\cdot9}=2^{48} \mathrm{bytes} = 265\mathrm{TiB}$$.

When the MMU needs to translate a virtual address, a page walk is performed.

 - Control register CR3 is read to obtain the physical address of the PML4.
 - Number the bits of the virtual address from 63 (high) to 0 (low).
 - Bits 47-39 are used as an index into the 512 PML4 entries, to select the PDPT
 - Bits 38-30 index into the PDPT, to give a page directory
 - Bits 29-20 index into the page directory, to give a page table
 - Bits 20-12 index into the page table, which contains the physical address of the page
 - Bits 0-11 then contain the offset into that page.

If the virtual address has already been translated in the recent past,
it will be cached in the Translation Lookaside Buffer (TLB) such that the time expensive page walk can be skipped.
Care should be taken that when the page table changes, the right (or just all) pages are invalidated in the TLB.
The architecture provides neat ways to do that, like process-context identifiers (PCIDs), but we can ignore those for now.

There is already a nice paging setup when the kernel main function is called,
otherwise we couldn't be in 64 bit mode.
However it doesn't allow for userspace (CPL=3) read/write/code execution in the
memory where our kernel is loaded.
So we have to take control of the paging system, and the easiest way is to build our own.
We'll just identity map (meaning virtual addresses map to identical physical addresses)
the whole 128MB address space and allow userspace read/write/code execution.

Section *4.5 IA-32E Paging* of the *Intel 64 and IA-32 Architectures Software Developer's Manuel
Volume 3A: System Programming Guide, Part 1*
contains the complete description of how paging works in 64 bit mode.
Its a good idea in general to give that a good read when developing a kernel.

A mapping table contains 512 8 byte entries and PML4 is the topmost mapping table:

```c
#pragma pack(1)

struct mapping_table {
    uint64_t entries[512];
};

#pragma pack()

__attribute__((aligned(4096)))
struct mapping_table pml4;
```

Next we load the PML4 such that it identity maps the entire address space.
Each entry in a mapping table contains a page aligned address (to either
another mapping table or a physical page). Since these addresses must
be page aligned, and there is a architectural maximum limit of 52 bits physical addresses,
there is room for bit flags in the entries.
The important flags for us are Present, Readable/Writable and User/Supervisor.
They must all be set to allow for user executable pages.


The next piece of code performs an identity map for one page.
It might look a bit involved due to the 4-level repetition.
Remember that we start with a completely empty PML4.
The code in essence performs a page walk, and every time an empty entry is
found it allocates space for a new mapping table and updates that entry.

```c
/* bitflags */
#define PAGE_BIT_P_PRESENT (1<<0)
#define PAGE_BIT_RW_WRITABLE (1<<1)
#define PAGE_BIT_US_USER (1<<2)
#define PAGE_XD_NX (1<<63)

/* bit mask for page aligned 52-bit address */
#define PAGE_ADDR_MASK 0x000ffffffffff000

/* these get updated when a page is accessed/written to */
#define PAGE_BIT_A_ACCESSED (1<<5)
#define PAGE_BIT_D_DIRTY (1<<6)

void identity_map_4kb(uint64_t logical) {
    /* flags: page is present, user readable and writable */
    int flags = PAGE_BIT_P_PRESENT | PAGE_BIT_RW_WRITABLE | PAGE_BIT_US_USER;

    /* extract mapping table indices from virtual address */
    int pml4_idx = (logical >> 39) & 0x1ff;
    int pdp_idx = (logical >> 30) & 0x1ff;
    int pd_idx = (logical >> 21) & 0x1ff;
    int pt_idx = (logical >> 12) & 0x1ff;
    int p_idx = logical & 0x7ff;

    /* did we define a PDPT for this PML4 index? */
    if (!(pml4.entries[pml4_idx] & PAGE_BIT_P_PRESENT)) {
        /* no, so lets allocate a new page for the PDPT */
        uint64_t pdpt_alloc = (uint64_t)alloc_page();
        /* zero it - this makes the PDPT an empty table with no PDTs present */
        memzero((void*)pdpt_alloc, 4096);
        /* now update the PML4 so it contains the new PDPT */
        pml4.entries[pml4_idx] = (pdpt_alloc & PAGE_ADDR_MASK) | flags;
        /* and make sure we can also access from our kernel
         * a bit redundant since we map the entire address space,
         * but needed when you map a smaller section */
        identity_map_4kb(pdpt_alloc);
    }

    /* get the PDPT given by the PML4 index */
    struct mapping_table * pdpt =
        (struct mapping_table*)(pml4.entries[pml4_idx] & PAGE_ADDR_MASK);
    /* and repeat the same process for the PDPT */
    if (!(pdpt->entries[pdp_idx] & PAGE_BIT_P_PRESENT)) {
        uint64_t pdt_alloc = (uint64_t)alloc_page();
        memzero((void*)pdt_alloc, 4096);
        pdpt->entries[pdp_idx] = (pdt_alloc & PAGE_ADDR_MASK) | flags;
        identity_map_4kb(pdt_alloc);
    }

    /* repeat the same process for the PDT */
    struct mapping_table * pdt =
        (struct mapping_table*)(pdpt->entries[pdp_idx] & PAGE_ADDR_MASK);
    if (!(pdt->entries[pd_idx] & PAGE_BIT_P_PRESENT)) {
        uint64_t pt_alloc = (uint64_t)alloc_page();
        memzero((void*)pt_alloc, 4096);
        pdt->entries[pd_idx] = (pt_alloc & PAGE_ADDR_MASK) | flags;
        identity_map_4kb(pt_alloc);
    }

    /* get the target PT */
    struct mapping_table * pt =
        (struct mapping_table*)(pdt->entries[pd_idx] & PAGE_ADDR_MASK);
    /* and update it such that it identity maps the given page */
    if (!(pt->entries[pt_idx] & PAGE_BIT_P_PRESENT)) {
        pt->entries[pt_idx] = (logical & PAGE_ADDR_MASK) | flags;
    }
}
```

Now we just need to call this function a few times
and update the CR3 register with our PML4 address:
A cleaner way would be to do this based on the UEFI memory map.

```c
extern void load_pml4(struct mapping_table * pml4);

void setup_paging() {
    memzero((void*)&pml4, 4096);
    for (int i = 0; i < 128*1024*1024; i+=4096) {
        identity_map_4kb(i);
    }
    load_pml4(&pml4);
}
```

```
.global load_pml4
load_pml4:
    mov rax, 0x000ffffffffff000
    and rdi, rax
    mov cr3, rdi
    ret
```

Nearly there! Now we just need update some model specific registers to execute a `sysret`.

# Enabling System Call Extensions and STAR

There are two things that need to happen before we can use `sysret`.
First, we need to enable the System Call Extensions (SCE).
Else, when we execute `sysret` we get an undefined opcode exception.
Next, we need to tell the cpu that executing `sysret` should... get us to
userspace by specifying which segment is the user base segment.

This happens via two model specific registers (MSRs), EFER and STAR, both introduced
by AMD. While they are technically model specific, they are now part of the architecture.
Reading and writing MSRs happens via loading their assigned address in RCX
and executing `rsmsr` or `wrmsr`. The contents are written to or loaded from `EDX:EAX`.
Pretty straighforward:

```
enable_sce:
    mov rcx, 0xc0000080 ; EFER MSR
    rdmsr               ; read current EFER
    or eax, 1           ; enable SCE bit
    wrmsr               ; write back new EFER
    mov rcx, 0xc0000081 ; STAR MSR
    rdmsr               ; read current STAR
    mov edx, 0x00180008 ; load up GDT segment bases 0x0 (kernel) and 0x18 (user)
    wrmsr               ; write back new STAR
    ret                 ; return back to C
```
# To (User)Space!

The final step! Or hopefully the beginning of a whole new kernel!

Lets start by defining a userspace entry point and some room for the stack:

```c
uint64_t user_stack[1024];

void user_function() {
    for(;;);
}
```

And a function that sets up the right registers and performs a `sysret`.

```
.global to_userspace
to_userspace:
    mov rcx, rdi        ; first argument, new instruction pointer
    mov rsp, rsi        ; second argument, new stack pointer
    mov r11, 0x0202     ; eflags
    sysretq;            ; to space!
```

Then call it. Remember that the stack grows down.

```c
to_userspace((void*)user_function, (void*)&user_stack[1023]);
```

Congratulations! If everything went well, you
should now be in privilege level 3.
Try executing a privileged instruction, like `wrmsr`
and a protection fault should happen.

# Next steps..

Thats up to you.
Adding support for `syscall` shouldn't be too hard now
(GDT and STAR are already in the right configuration,
you need to load the kernel entry point in the LSTAR MSR).
Then add a struct task to your kernel and try to get
cooperative multiprocessing working.
Or first take a look at getting graphics working
by getting to a known VGA mode via the UEFI graphics protocol.
Having a working IDT is also a good idea.

Good luck!
