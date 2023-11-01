# Set to 1 if building an empty subscription-only package.
%define empty_package		0

#######################################################
# Only need to update these variables and the changelog
%define kernel_ver	4.18.0-193.el8
%define kpatch_ver	0.9.1
%define rpm_ver		1
%define rpm_rel		7

%if !%{empty_package}
# Patch sources below. DO NOT REMOVE THIS LINE.
#
# https://bugzilla.redhat.com/1827332
Source100: v2-netlabel-cope-with-NULL-catmap.patch
#
# https://bugzilla.redhat.com/1835531
Source101: block-block-bfq-fix-use-after-free-in-bfq_idle_slice.patch
#
# https://bugzilla.redhat.com/1847371
Source102: x86-speculation-Prevent-rogue-cross-process-SSBD-shu.patch
#
# https://bugzilla.redhat.com/1847404
# https://bugzilla.redhat.com/1847402
Source103: kpatch-adapted-patch-for-CVE-2020-10767-and-CVE-2020-10768.patch
#
# https://bugzilla.redhat.com/1881426
Source104: net-packet-make-tp_drops-atomic.patch
#
# https://bugzilla.redhat.com/1881416
Source105: fs-xfs-fix-boundary-test-in-xfs_attr_shortform_verify.patch
# End of patch sources. DO NOT REMOVE THIS LINE.
%endif

%define sanitized_rpm_rel	%{lua: print((string.gsub(rpm.expand("%rpm_rel"), "%.", "_")))}
%define sanitized_kernel_ver   %{lua: print((string.gsub(string.gsub(rpm.expand("%kernel_ver"), '.el8_?\%d?', ""), "%.", "_")))}
%define kernel_ver_arch        %{kernel_ver}.%{_arch}

Name:		kpatch-patch-%{sanitized_kernel_ver}
Version:	%{rpm_ver}
Release:	%{rpm_rel}%{?dist}

%if %{empty_package}
Summary:	Initial empty kpatch-patch for kernel-%{kernel_ver_arch}
%else
Summary:	Live kernel patching module for kernel-%{kernel_ver_arch}
%endif

Group:		System Environment/Kernel
License:	GPLv2
ExclusiveArch:	x86_64 ppc64le

Conflicts:	%{name} < %{version}-%{release}

Provides:	kpatch-patch = %{kernel_ver_arch}
Provides:	kpatch-patch = %{kernel_ver}

%if !%{empty_package}
Requires:	systemd
%endif
Requires:	kpatch >= 0.6.1-1
Requires:	kernel-uname-r = %{kernel_ver_arch}

%if !%{empty_package}
BuildRequires:	patchutils
BuildRequires:	kernel-devel = %{kernel_ver}
BuildRequires:	kernel-debuginfo = %{kernel_ver}

# kernel build requirements, generated from:
#   % rpmspec -q --buildrequires kernel.spec | sort | awk '{print "BuildRequires:\t" $0}'
# with arch-specific packages moved into conditional block
BuildRequires:	asciidoc audit-libs-devel bash bc binutils binutils-devel bison bzip2 diffutils elfutils elfutils-devel findutils flex gawk gcc gettext git gzip hmaccalc hostname kmod m4 make ncurses-devel net-tools newt-devel numactl-devel openssl openssl-devel patch pciutils-devel perl-Carp perl-devel perl(ExtUtils::Embed) perl-generators perl-interpreter python3-devel python3-docutils redhat-rpm-config rpm-build sh-utils tar xmlto xz xz-devel zlib-devel java-devel kabi-dw

%ifarch x86_64
BuildRequires:	pesign >= 0.10-4
%endif

%ifarch ppc64le
BuildRequires:	gcc-plugin-devel
%endif

Source0:	https://github.com/dynup/kpatch/archive/v%{kpatch_ver}.tar.gz

Source10:	kernel-%{kernel_ver}.src.rpm

# kpatch-build patches
Patch1: create-diff-object-ignore-altrinstr-aux-backport.patch

%global _dupsign_opts --keyname=rhelkpatch1

%define builddir	%{_builddir}/kpatch-%{kpatch_ver}
%define kpatch		%{_sbindir}/kpatch
%define kmoddir 	%{_usr}/lib/kpatch/%{kernel_ver_arch}
%define kinstdir	%{_sharedstatedir}/kpatch/%{kernel_ver_arch}
%define patchmodname	kpatch-%{sanitized_kernel_ver}-%{version}-%{sanitized_rpm_rel}
%define patchmod	%{patchmodname}.ko

%define _missing_build_ids_terminate_build 1
%define _find_debuginfo_opts -r
%undefine _include_minidebuginfo
%undefine _find_debuginfo_dwz_opts

%description
This is a kernel live patch module which can be loaded by the kpatch
command line utility to modify the code of a running kernel.  This patch
module is targeted for kernel-%{kernel_ver}.

%prep
%autosetup -n kpatch-%{kpatch_ver} -p1

%build
kdevdir=/usr/src/kernels/%{kernel_ver_arch}
vmlinux=/usr/lib/debug/lib/modules/%{kernel_ver_arch}/vmlinux

# kpatch-build
make -C kpatch-build

# patch module
for i in %{sources}; do
	[[ $i == *.patch ]] && patch_sources="$patch_sources $i"
done
export CACHEDIR="%{builddir}/.kpatch"
kpatch-build/kpatch-build -n %{patchmodname} -r %{SOURCE10} -v $vmlinux --skip-cleanup $patch_sources || { cat "${CACHEDIR}/build.log"; exit 1; }


%install
installdir=%{buildroot}/%{kmoddir}
install -d $installdir
install -m 755 %{builddir}/%{patchmod} $installdir


%files
%{_usr}/lib/kpatch


%post
%{kpatch} install -k %{kernel_ver_arch} %{kmoddir}/%{patchmod}
chcon -t modules_object_t %{kinstdir}/%{patchmod}
sync
if [[ %{kernel_ver_arch} = $(uname -r) ]]; then
	cver="%{rpm_ver}_%{rpm_rel}"
	pname=$(echo "kpatch_%{sanitized_kernel_ver}" | sed 's/-/_/')

	lver=$({ %{kpatch} list | sed -nr "s/^${pname}_([0-9_]+)\ \[enabled\]$/\1/p"; echo "${cver}"; } | sort -V | tail -1)

	if [ "${lver}" != "${cver}" ]; then
		echo "WARNING: at least one loaded kpatch-patch (${pname}_${lver}) has a newer version than the one being installed."
		echo "WARNING: You will have to reboot to load a downgraded kpatch-patch"
	else
		%{kpatch} load %{patchmod}
	fi
fi
exit 0


%postun
%{kpatch} uninstall -k %{kernel_ver_arch} %{patchmod}
sync
exit 0

%else
%description
This is an empty kpatch-patch package which does not contain any real patches.
It is only a method to subscribe to the kpatch stream for kernel-%{kernel_ver}.

%files
%doc
%endif

%changelog
* Tue Oct 06 2020 Julien Thierry <jthierry@redhat.com> [1-7.el8]
- xfs: fix boundary test in xfs_attr_shortform_verify [1881416] {CVE-2020-14385}

* Wed Sep 23 2020 Artem Savkov <asavkov@redhat.com> [1-6.el8]
- memory corruption in net/packet/af_packet.c leads to elevation of privilege [1881426] {CVE-2020-14386}

* Fri Jun 26 2020 Artem Savkov <asavkov@redhat.com> [1-5.el8]
- Indirect Branch Prediction Barrier is force-disabled when STIBP is unavailable or enhanced IBRS is available. Indirect branch speculation can be enabled after it was force-disabled by the PR_SPEC_FORCE_DISABLE prctl command. [1847404] [1847402] {CVE-2020-10767} {CVE-2020-10768}

* Thu Jun 25 2020 Julien Thierry <jthierry@redhat.com> [1-4.el8]
- Prevent rogue cross-process SSBD shutdown [1847371] {CVE-2020-10766}

* Mon May 25 2020 Artem Savkov <asavkov@redhat.com> [1-3.el8]
- use-after-free in block/bfq-iosched.c related to bfq_idle_slice_timer_body [1835531] {CVE-2020-12657}

* Mon May 11 2020 Joe Lawrence <joe.lawrence@redhat.com> [1-2.el8]
- Workaround kpatch ppc64le leaf functions in previous patch [1827332] {CVE-2020-10711}

* Fri May 08 2020 Joe Lawrence <joe.lawrence@redhat.com> [1-1.el8]
- netlabel: cope with NULL catmap [1827332] {CVE-2020-10711}

* Fri Apr 10 2020 Joe Lawrence <joe.lawrence@redhat.com> [0-0.el8]
- An empty patch to subscribe to kpatch stream for kernel-4.18.0-193.el8 [1822309]
