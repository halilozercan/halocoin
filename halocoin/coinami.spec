# -*- mode: python -*-

block_cipher = None


a = Analysis(['cli.py'],
             pathex=[],
             binaries=[],
             datas=[],
             hiddenimports=['engineio.async_eventlet', 'dns', 'dns.dnssec', 'dns.e164', 'dns.namedict',
             'dns.tsigkeyring', 'dns.update', 'dns.version', 'dns.zone'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='coinami',
          debug=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=True )
