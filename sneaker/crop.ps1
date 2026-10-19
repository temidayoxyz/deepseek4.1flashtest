function Crop($src, $dst, $x, $y, $w, $h, $scale) {
  Add-Type -AssemblyName System.Drawing
  $b = [System.Drawing.Bitmap]::FromFile((Resolve-Path $src))
  $nw = [int]($w * $scale); $nh = [int]($h * $scale)
  $out = New-Object System.Drawing.Bitmap $nw, $nh
  $g = [System.Drawing.Graphics]::FromImage($out)
  $g.InterpolationMode = 'NearestNeighbor'
  $g.DrawImage($b, (New-Object System.Drawing.Rectangle 0,0,$nw,$nh),
               (New-Object System.Drawing.Rectangle $x,$y,$w,$h), 'Pixel')
  $out.Save((Join-Path (Get-Location) $dst), [System.Drawing.Imaging.ImageFormat]::Png)
  $g.Dispose(); $out.Dispose(); $b.Dispose()
  "wrote $dst"
}
