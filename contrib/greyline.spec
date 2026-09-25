# greyline — RPM spec for the Fedora COPR repo (cothinking/greyline).
#
# Built from the PyPI sdist, not a git tarball: the sdist is what PyPI users already
# get, and it carries LICENSE, NOTICE and the full tests/ tree, so %%check runs the
# real suite. Two tests self-skip in a buildroot — test_wiki_docs.py (tools/ is not in
# the sdist) and test_js_port.py (no node) — so neither needs a BuildRequires.
#
# Classic explicit macro style rather than Fedora 42+'s declarative `BuildSystem:
# pyproject`, so that one spec covers every enabled chroot including EPEL 10.
#
# Version is kept in step with pyproject.toml by the release workflow; see
# .github/workflows/publish.yml.

Name:           greyline
Version:        0.8.7
Release:        1%{?dist}
Summary:        A live world-time desktop wallpaper for Wayland and X11

# Matches the PEP 639 SPDX expression in pyproject.toml.
License:        GPL-2.0-or-later
URL:            https://github.com/Jotham-LEC/greyline
Source:         %{pypi_source greyline}

BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  python3dist(pytest)

# fc-match resolves the configured font family; without it the renderer falls back to
# a bundled candidate list (see greyline/render.py). Not fatal, so a weak dependency.
Recommends:     fontconfig
# The Linux entries in that fallback chain are DejaVuSans / DejaVuSans-Bold.
Recommends:     dejavu-sans-fonts

# Wallpaper backends. All are probed with shutil.which() and any one of them is
# enough, so none is a hard requirement.
Suggests:       swaybg
Suggests:       swww
Suggests:       hyprpaper
Suggests:       feh
Suggests:       xwallpaper

%description
greyline draws a world map as your desktop wallpaper, with clocks for the cities you
pick, your home city marked, and a day/night terminator that tracks the sun. It is a
modern recreation of the IBM/ThinkPad "World Time" Active Desktop.

There is no daemon and no browser behind it. A systemd user timer runs greyline once a
minute: it renders a PNG per output, hands each to the wallpaper mechanism you already
use, and exits. Thirty-five themes ship, light and dark, most of them ports of the
base16 schemes your editor and terminal already use.

Run `greyline init` after installing: it detects your compositor, picks a backend,
writes ~/.config/greyline/config.toml and enables the user timer.

%prep
%autosetup -n greyline-%{version} -p1

%generate_buildrequires
%pyproject_buildrequires -r

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files greyline

# Deliberately NOT installing systemd/greyline.{service,timer}. greyline/service.py
# generates those units into ~/.config/systemd/user at `greyline init` time, resolving
# ExecStart via shutil.which("greyline") — which finds %{_bindir}/greyline correctly.
# Shipping the repo's reference copies to %%{_userunitdir} would create a second unit
# definition that the user-level one silently shadows.

%check
%pyproject_check_import
%pytest

%files -f %{pyproject_files}
%license LICENSE NOTICE
%doc README.md
# %%pyproject_save_files covers sitelib only; the console script needs listing.
%{_bindir}/greyline

%changelog
* Fri Sep 25 2026 Jotham Lim Ee Chen <jotham@cothink.ing> - 0.8.7-1
- Update to 0.8.7: the sdist now ships tests/conftest.py, so %%check passes.

* Thu Sep 24 2026 Jotham Lim Ee Chen <jotham@cothink.ing> - 0.8.6-1
- Packaged for COPR. Per-release notes live in the project's CHANGELOG.md:
  https://github.com/Jotham-LEC/greyline/blob/main/CHANGELOG.md
