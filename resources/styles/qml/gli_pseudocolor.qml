<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>

<qgis version="3.34.12-Prizren" styleCategories="AllStyleCategories" maxScale="0" hasScaleBasedVisibilityFlag="0" minScale="1e+08" autoRefreshMode="Disabled" autoRefreshTime="0">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>1</Searchable>
    <Private>0</Private>
  </flags>
  <temporal fetchMode="0" enabled="0" mode="0">
    <fixedRange>
      <start/>
      <end/>
    </fixedRange>
  </temporal>
  <elevation zoffset="0" symbology="Line" enabled="0" band="1" zscale="1"/>
  <pipe>
    <provider>
      <resampling zoomedOutResamplingMethod="nearestNeighbour" enabled="false" maxOversampling="2" zoomedInResamplingMethod="nearestNeighbour"/>
    </provider>
    <rasterrenderer alphaBand="-1" blueBand="-1" type="singlebandpseudocolor" greenBand="-1" nodataColor="" band="1" redBand="-1" opacity="1.0" classificationMin="-1" classificationMax="1">
      <rasterTransparency/>
      <minMaxOrigin>
        <limits>None</limits>
        <extent>WholeRaster</extent>
        <statAccuracy>Estimated</statAccuracy>
        <cumulativeCutLower>0.02</cumulativeCutLower>
        <cumulativeCutUpper>0.98</cumulativeCutUpper>
        <stdDevFactor>2</stdDevFactor>
      </minMaxOrigin>
      <colorPalette>
        <paletteEntry value="-1.000000" color="#8B4513" label="-1.000000" alpha="255"/>
        <paletteEntry value="-0.500000" color="#D2691E" label="-0.500000" alpha="255"/>
        <paletteEntry value="-0.200000" color="#EDC848" label="-0.200000" alpha="255"/>
        <paletteEntry value="0.000000" color="#FFFF00" label="0.000000" alpha="255"/>
        <paletteEntry value="0.200000" color="#ADFF2F" label="0.200000" alpha="255"/>
        <paletteEntry value="0.400000" color="#7CFC00" label="0.400000" alpha="255"/>
        <paletteEntry value="0.600000" color="#32CD32" label="0.600000" alpha="255"/>
        <paletteEntry value="0.800000" color="#228B22" label="0.800000" alpha="255"/>
        <paletteEntry value="1.000000" color="#006400" label="1.000000" alpha="255"/>
      </colorPalette>
      <contrastEnhancement>
        <minValue>-1.0000000</minValue>
        <maxValue>1.0000000</maxValue>
        <algorithm>StretchToMinimumMaximum</algorithm>
      </contrastEnhancement>
    </rasterrenderer>
    <brightnesscontrast brightness="0" gamma="1" contrast="0"/>
    <huesaturation colorizeGreen="128" grayscaleMode="0" invertColors="0" colorizeStrength="100" colorizeBlue="128" colorizeRed="255" saturation="0" colorizeOn="0"/>
    <rasterresampler maxOversampling="2"/>
    <resamplingStage>resamplingFilter</resamplingStage>
  </pipe>
  <blendMode>0</blendMode>
</qgis>