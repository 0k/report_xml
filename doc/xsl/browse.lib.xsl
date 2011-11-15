<?xml version='1.0' encoding="utf-8"?>
<xsl:stylesheet
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
	xmlns:xs="http://www.w3.org/2001/XMLSchema"
        xmlns:g="http://www.graphane.com"
	version='2.0'>

  <!-- TEMPLATE / FUNCTION -->

  <!-- keep ref to the root document -->
  <xsl:variable name="root" select="/" />

  <!-- Recursively unfold the path to browse into XML attributes -->
  <xsl:template name="_browse_rec">
    <xsl:param name="path" as="xs:string" />
    <xsl:param name="table" as="xs:string" />
    <xsl:param name="id" as="xs:string" />

    <xsl:variable name="attrib"
                  select="if (contains($path, '.')) then (substring-before($path, '.')) else ($path)" />
    <xsl:variable name="remaining"
                  select="if (contains($path, '.')) then (substring-after($path, '.')) else ''" />

    <xsl:choose>
      <xsl:when test="$attrib = ''">
        <xsl:sequence select="." />
      </xsl:when>
      <xsl:when test="$root/report/data/*[name() = $table and @id = $id]/*[name() = $attrib]">
        <xsl:for-each select="$root/report/data/*[name() = $table and @id = $id]/*[name() = $attrib]">
          <xsl:choose>
            <xsl:when test="$remaining != ''">
              <xsl:call-template name="_browse_rec">
                <xsl:with-param name="table" select="@table"/>
                <xsl:with-param name="id" select="@id"/>
                <xsl:with-param name="path" select="$remaining"/>
              </xsl:call-template>
            </xsl:when>
            <xsl:otherwise>
              <xsl:sequence select="node()" />
            </xsl:otherwise>
          </xsl:choose>
        </xsl:for-each>
      </xsl:when>
      <xsl:otherwise>
        <xsl:message>
          PATH '<xsl:value-of select="$attrib" />' NOT FOUND
          Please verify this path exists in object <xsl:value-of select="$table" />:<xsl:value-of select="$id" />
          Please choose a tag from: <xsl:value-of separator=", " select="$root/report/data/*[name() = $table and @id = $id]/*/name()" />
        </xsl:message>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <!--
      Fetches the $root/report/requests/request as root for the browse command
      and launch the recursive browse on it -->
  <xsl:template name="_browse_obj">
    <xsl:param name="obj" />
    <xsl:param name="path" as="xs:string" />
    <!-- XXXvlab: Does not support more than one element in requests -->
    <!-- for-each is used on only one element, this is to load a defined context -->
    <xsl:for-each select="$obj">
      <xsl:call-template name="_browse_rec">
        <xsl:with-param name="path" select="$path"/>
        <xsl:with-param name="table" select="$obj/@table"/>
        <xsl:with-param name="id" select="$obj/@id"/>
      </xsl:call-template>
    </xsl:for-each>
  </xsl:template>

  <xsl:function name="g:browse">
    <xsl:param name="obj" />
    <xsl:param name="path" as="xs:string"/>
    <xsl:call-template name="_browse_obj">
      <xsl:with-param name="obj" select="$obj"/>
      <xsl:with-param name="path" select="$path"/>
    </xsl:call-template>
  </xsl:function>


  <!-- 
       Will create elements for each variable
    -->
  <xsl:function name="g:vars">
    <xsl:param name="obj" />
    <xsl:param name="path" as="xs:string"/>

    <xsl:variable name="first"
                  select="normalize-space(if (contains($path, ',')) then (substring-before($path, ',')) else ($path))" />
    <xsl:variable name="remaining"
                  select="normalize-space(if (contains($path, ',')) then (substring-after($path, ',')) else '')" />

    <xsl:element name="{$first}">
      <xsl:sequence select="g:browse($obj, $first)" />
    </xsl:element>

    <xsl:choose>
      <xsl:when test="$remaining != ''">
        <xsl:sequence select="g:vars($obj, $remaining)" />
      </xsl:when>
    </xsl:choose>
  </xsl:function>

</xsl:stylesheet>
