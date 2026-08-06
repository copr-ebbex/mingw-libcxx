# The LLVM C++ runtime stack -- libunwind, libc++abi and libc++ -- for the
# aarch64-w64-mingw32 (Windows on ARM64) target.
#
# Only the LLVM based target has these runtimes; the GCC targets use libstdc++
# and the GCC unwinder out of mingw-gcc, so every other target is off here.
#
# Note: LLVM no longer publishes per-project source tarballs, and the runtimes
# are configured through runtimes/CMakeLists.txt (LLVM_ENABLE_RUNTIMES), which
# reaches across the whole tree, so the complete llvm-project monorepo tarball
# is Source0 and only runtimes/ is configured and built.
%global mingw_build_win32     0
%global mingw_build_win64     0
%global mingw_build_ucrt64    0
%global mingw_build_ucrtarm64 1

# Nils the brp strip passes for the ucrtarm64 target (binutils strip corrupts
# AArch64 PE archives); %%check verifies the ar symbol indexes survived.
%{?mingw_package_header}

Name:           mingw-libcxx
Version:        22.1.8
Release:        1%{?dist}
Summary:        MinGW cross-compiled LLVM C++ runtime

License:        Apache-2.0 WITH LLVM-exception OR NCSA
URL:            https://libcxx.llvm.org/
BuildArch:      noarch

Source0:        https://github.com/llvm/llvm-project/releases/download/llvmorg-%{version}/llvm-project-%{version}.src.tar.xz

BuildRequires:  cmake
BuildRequires:  ninja-build
BuildRequires:  python3
BuildRequires:  ucrtarm64-filesystem >= 152
BuildRequires:  ucrtarm64-headers
BuildRequires:  ucrtarm64-crt
BuildRequires:  ucrtarm64-clang
BuildRequires:  ucrtarm64-compiler-rt
# For %%check, which inspects the archives and the linked PE images.
BuildRequires:  llvm


%description
The LLVM C++ runtime stack cross-compiled for MinGW targets: libunwind,
libc++abi and libc++.

The aarch64-w64-mingw32 target has no libstdc++ or GCC unwinder, as it is
driven by clang and lld rather than by GCC, so the C++ runtime comes from
LLVM instead.


%package -n ucrtarm64-libunwind
Summary:        LLVM unwinder for the Windows on ARM64 target
Requires:       ucrtarm64-crt

%description -n ucrtarm64-libunwind
The LLVM unwinder for the aarch64-w64-mingw32 target.

This is what -unwindlib=libunwind links against, in place of the GCC unwinder
that the GCC based MinGW targets use.  It is needed by anything that throws,
including C code built with exceptions enabled.


%package -n ucrtarm64-libunwind-static
Summary:        Static version of the LLVM unwinder for the Windows on ARM64 target
Requires:       ucrtarm64-libunwind = %{version}-%{release}

%description -n ucrtarm64-libunwind-static
Static version of the LLVM unwinder for the aarch64-w64-mingw32 target.

This is what -unwindlib=libunwind resolves to in a -static link.


%package -n ucrtarm64-libcxxabi
Summary:        LLVM C++ ABI library for the Windows on ARM64 target
Requires:       ucrtarm64-libunwind = %{version}-%{release}

%description -n ucrtarm64-libcxxabi
The LLVM C++ ABI support library for the aarch64-w64-mingw32 target.

There is no shared libc++abi on this target: its objects are linked into
libc++.dll and into libc++.a instead.  This package therefore carries only the
ABI headers, which libc++'s own headers include; the archive is in
ucrtarm64-libcxxabi-static.


%package -n ucrtarm64-libcxxabi-static
Summary:        Static version of the LLVM C++ ABI library for the Windows on ARM64 target
Requires:       ucrtarm64-libcxxabi = %{version}-%{release}

%description -n ucrtarm64-libcxxabi-static
Static version of the LLVM C++ ABI support library for the
aarch64-w64-mingw32 target.

Only needed to link the ABI library on its own; ucrtarm64-libcxx-static
already has these objects merged into libc++.a.


%package -n ucrtarm64-libcxx
Summary:        LLVM C++ standard library for the Windows on ARM64 target
Requires:       ucrtarm64-libcxxabi = %{version}-%{release}

%description -n ucrtarm64-libcxx
The LLVM C++ standard library for the aarch64-w64-mingw32 target.

This is what -stdlib=libc++ links against, in place of the libstdc++ that the
GCC based MinGW targets use.


%package -n ucrtarm64-libcxx-static
Summary:        Static version of the LLVM C++ standard library for the Windows on ARM64 target
Requires:       ucrtarm64-libcxx = %{version}-%{release}
Requires:       ucrtarm64-libunwind-static = %{version}-%{release}

%description -n ucrtarm64-libcxx-static
Static version of the LLVM C++ standard library for the aarch64-w64-mingw32
target, plus the experimental library.

libc++abi is merged into libc++.a, but a -static link still resolves
-unwindlib=libunwind against libunwind.a, hence the dependency on
ucrtarm64-libunwind-static.

# Required with %%mingw_package_header for stripped DLLs plus debuginfo.
%{?mingw_debug_package}


%prep
%autosetup -p1 -n llvm-project-%{version}.src


%build
# The stack is version-locked to the chroot clang major (see
# mingw-compiler-rt); fail loudly on a clang rebase instead of building a
# mismatched runtime.
test "$(echo %{version} | cut -d. -f1)" = "%{clang_major_version}"

# NB. not exported: %%{ucrtarm64_env} unsets every exported variable, so the
# per-target *_CMAKE_ARGS have to be plain shell variables to survive it.
pushd runtimes
    # CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY is mandatory: no link can
    # succeed before these runtimes exist.  It also makes every -l<foo> probe
    # succeed vacuously, so every LIB*_HAS_*_LIB knob is answered OFF by hand.
    # Threading is the Win32 API, as in llvm-mingw; %%check proves it.
    UCRTARM64_CMAKE_ARGS="\\
        -DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY \\
        -DLLVM_ENABLE_RUNTIMES=libunwind;libcxxabi;libcxx \\
        -DLIBUNWIND_USE_COMPILER_RT=ON \\
        -DLIBUNWIND_ENABLE_SHARED=ON \\
        -DLIBUNWIND_ENABLE_STATIC=ON \\
        -DLIBCXXABI_USE_COMPILER_RT=ON \\
        -DLIBCXXABI_USE_LLVM_UNWINDER=ON \\
        -DLIBCXXABI_ENABLE_SHARED=OFF \\
        -DLIBCXXABI_ENABLE_STATIC=ON \\
        -DLIBCXX_USE_COMPILER_RT=ON \\
        -DLIBCXX_CXX_ABI=libcxxabi \\
        -DLIBCXX_ENABLE_SHARED=ON \\
        -DLIBCXX_ENABLE_STATIC=ON \\
        -DLIBCXX_ENABLE_STATIC_ABI_LIBRARY=ON \\
        -DLIBCXX_ENABLE_ABI_LINKER_SCRIPT=OFF \\
        -DLIBCXX_HAS_WIN32_THREAD_API=ON \\
        -DLIBCXXABI_HAS_WIN32_THREAD_API=ON \\
        -DLIBCXX_ENABLE_FILESYSTEM=ON \\
        -DLIBUNWIND_HAS_BSD_LIB=OFF \\
        -DLIBUNWIND_HAS_C_LIB=OFF \\
        -DLIBUNWIND_HAS_DL_LIB=OFF \\
        -DLIBUNWIND_HAS_GCC_LIB=OFF \\
        -DLIBUNWIND_HAS_GCC_S_LIB=OFF \\
        -DLIBUNWIND_HAS_PTHREAD_LIB=OFF \\
        -DLIBUNWIND_HAS_ROOT_LIB=OFF \\
        -DLIBCXXABI_HAS_C_LIB=OFF \\
        -DLIBCXXABI_HAS_DL_LIB=OFF \\
        -DLIBCXXABI_HAS_GCC_LIB=OFF \\
        -DLIBCXXABI_HAS_GCC_S_LIB=OFF \\
        -DLIBCXXABI_HAS_PTHREAD_LIB=OFF \\
        -DLIBCXX_HAS_ATOMIC_LIB=OFF \\
        -DLIBCXX_HAS_GCC_LIB=OFF \\
        -DLIBCXX_HAS_GCC_S_LIB=OFF \\
        -DLIBCXX_HAS_MUSL_LIB=OFF \\
        -DLIBCXX_HAS_PTHREAD_LIB=OFF \\
        -DLIBCXX_HAS_RT_LIB=OFF"
    %mingw_cmake -G Ninja
    %mingw_ninja
popd


%install
pushd runtimes
    %mingw_ninja_install
popd

# libunwind ships the Mach-O compact unwind encoding header unconditionally.
# It describes a format this target cannot produce or consume, so it is not
# shipped rather than being packaged into a Windows sysroot.
rm -rf %{buildroot}%{ucrtarm64_includedir}/mach-o


%check
libdir=%{buildroot}%{ucrtarm64_libdir}
bindir=%{buildroot}%{ucrtarm64_bindir}

# 1. Every shipped archive -- static libraries and import libraries alike --
#    must still carry its ar symbol index.  %%check runs after the buildroot
#    policy scripts, so this is what catches a stripper having eaten it.
#
#    A GNU archive carries the symbol table as its first member, named "/", so
#    the first ten bytes are "!<arch>\n" followed by "/ ".  An index-less
#    archive starts with the long name table "//" instead.
found_archives=0
for a in "$libdir"/*.a ; do
    test -f "$a" || continue
    found_archives=$(( found_archives + 1 ))
    header=$(od -A n -t x1 -N 10 "$a" | tr -d ' \n')
    echo "archive $a header bytes: $header members: $(llvm-ar t "$a" | wc -l)"
    test "$header" = "213c617263683e0a2f20"
    llvm-nm --print-armap "$a" | grep -q ' in ' || \
        { echo "ar symbol index of $a does not resolve" ; exit 1 ; }
done
echo "archives checked: $found_archives"
test "$found_archives" -ge 6

# 2. Every shipped DLL must be AArch64 PE, and libc++.dll must import the
#    unwinder -- that import is what the rpm dependency generator turns into
#    the ucrtarm64(libunwind.dll) requirement.
found_dlls=0
for d in "$bindir"/*.dll ; do
    test -f "$d" || continue
    found_dlls=$(( found_dlls + 1 ))
    llvm-objdump -f "$d"
    llvm-objdump -f "$d" | grep -q 'coff-arm64'
done
echo "DLLs checked: $found_dlls"
test "$found_dlls" -eq 2
llvm-readobj --coff-imports "$bindir/libc++.dll" | grep -q 'Name: libunwind.dll'

# 3. The point of the package: compile and link a real C++ program, with a
#    thrown exception and a std::thread, against the runtimes that are about
#    to be shipped.
#
#    They are not installed yet, so the sysroot copies do not exist: -isystem
#    puts the buildroot C++ headers ahead of the (absent) sysroot ones and -L
#    puts the buildroot libraries on the link line.  The compiler-rt builtins
#    are a build dependency and are already installed in clang's resource
#    directory, so no -resource-dir farm is needed here.
cat > _thread_probe.cpp <<'EOF'
#include <cstdio>
#include <stdexcept>
#include <string>
#include <thread>

int main()
{
    std::string out;
    std::thread t([&] { out = "std::thread on aarch64-w64-mingw32"; });
    t.join();

    try {
        throw std::runtime_error("unwound");
    } catch (const std::exception &e) {
        std::printf("%s, exception: %s\n", out.c_str(), e.what());
    }
    return 0;
}
EOF

probe_flags="-isystem %{buildroot}%{ucrtarm64_includedir}/c++/v1 -L%{buildroot}%{ucrtarm64_libdir}"

# 3a. Shared: the exe must be AArch64 PE and must import libc++.dll.
%{ucrtarm64_target}-clang++ $probe_flags -o _thread_probe.exe _thread_probe.cpp
llvm-objdump -f _thread_probe.exe
llvm-objdump -f _thread_probe.exe | grep -q 'coff-arm64'
llvm-readobj --coff-imports _thread_probe.exe | grep 'Name:'
llvm-readobj --coff-imports _thread_probe.exe | grep -q 'Name: libc++.dll'

# 3b. Static: the same program must link against libc++.a plus libunwind.a,
#     and then must NOT import either DLL.
%{ucrtarm64_target}-clang++ $probe_flags -static -o _thread_probe_static.exe \
    _thread_probe.cpp
llvm-objdump -f _thread_probe_static.exe | grep -q 'coff-arm64'
if llvm-readobj --coff-imports _thread_probe_static.exe | \
       grep -qE 'Name: (libc\+\+|libunwind)\.dll' ; then
    echo "the -static link still imports a runtime DLL"
    exit 1
fi

# 4. std::thread must be the Win32 thread API, not winpthreads: nothing in the
#    stack provides pthreads, so an import of libwinpthread would mean the
#    build picked up a threading model this package does not depend on, and a
#    reference to pthread_create would mean it picked up none at all.
if llvm-readobj --coff-imports _thread_probe.exe | grep -qi 'winpthread' ; then
    echo "the probe imports winpthreads; expected the Win32 thread API"
    exit 1
fi
llvm-nm --undefined-only _thread_probe_static.exe > _undef.txt || :
if grep -q 'pthread_create' _undef.txt ; then
    echo "unresolved pthread_create: LIBCXX_HAS_WIN32_THREAD_API did not take"
    exit 1
fi
#    The threading model is visible in libc++.a itself: the Win32 API build
#    compiles src/support/win32/thread_win32.cpp, which creates threads with
#    the CRT's _beginthreadex.  A pthread build would compile neither and would
#    leave pthread_create undefined instead.
llvm-ar t "$libdir/libc++.a" | grep -q 'thread_win32' || \
    { echo "libc++.a has no thread_win32 member" ; exit 1 ; }
llvm-nm --undefined-only "$libdir/libc++.a" | grep -q '_beginthreadex' || \
    { echo "libc++.a does not reference _beginthreadex" ; exit 1 ; }
if llvm-nm --undefined-only "$libdir/libc++.a" | grep -q 'pthread_create' ; then
    echo "libc++.a references pthread_create"
    exit 1
fi
echo "check: std::thread uses the Win32 thread API"

# 5. Nothing Mach-O may be shipped into a Windows sysroot.
test ! -e %{buildroot}%{ucrtarm64_includedir}/mach-o


%files -n ucrtarm64-libunwind
%license libunwind/LICENSE.TXT
%{ucrtarm64_bindir}/libunwind.dll
%{ucrtarm64_libdir}/libunwind.dll.a
%{ucrtarm64_includedir}/__libunwind_config.h
%{ucrtarm64_includedir}/libunwind.h
%{ucrtarm64_includedir}/libunwind.modulemap
%{ucrtarm64_includedir}/unwind.h
%{ucrtarm64_includedir}/unwind_arm_ehabi.h
%{ucrtarm64_includedir}/unwind_itanium.h

%files -n ucrtarm64-libunwind-static
%license libunwind/LICENSE.TXT
%{ucrtarm64_libdir}/libunwind.a

%files -n ucrtarm64-libcxxabi
%license libcxxabi/LICENSE.TXT
# Shared with ucrtarm64-libcxx: libc++abi installs its headers into libc++'s
# own header directory, so both packages own the directories.
%dir %{ucrtarm64_includedir}/c++
%dir %{ucrtarm64_includedir}/c++/v1
%{ucrtarm64_includedir}/c++/v1/__cxxabi_config.h
%{ucrtarm64_includedir}/c++/v1/cxxabi.h

%files -n ucrtarm64-libcxxabi-static
%license libcxxabi/LICENSE.TXT
%{ucrtarm64_libdir}/libc++abi.a

%files -n ucrtarm64-libcxx
%license libcxx/LICENSE.TXT
%{ucrtarm64_bindir}/libc++.dll
%{ucrtarm64_libdir}/libc++.dll.a
%{ucrtarm64_libdir}/libc++.modules.json
%{ucrtarm64_includedir}/c++/
%exclude %{ucrtarm64_includedir}/c++/v1/__cxxabi_config.h
%exclude %{ucrtarm64_includedir}/c++/v1/cxxabi.h
# The C++23 std module sources, which libc++ installs for building `import std`
%{ucrtarm64_datadir}/libc++/

%files -n ucrtarm64-libcxx-static
%license libcxx/LICENSE.TXT
%{ucrtarm64_libdir}/libc++.a
%{ucrtarm64_libdir}/libc++experimental.a


%changelog
* Thu Aug 06 2026 Erik Berg <fedora@slipsprogrammor.no> - 22.1.8-1
- Initial package: the LLVM C++ runtime stack (libunwind, libc++abi, libc++)
  for the aarch64-w64-mingw32 (ucrtarm64) target
- Threading is the Win32 thread API, as in llvm-mingw, so nothing here needs
  winpthreads
- Static libraries are in -static subpackages of their own
- The Mach-O compact unwind header libunwind installs unconditionally is not
  shipped into a Windows sysroot
