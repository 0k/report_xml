<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:g="http://www.graphane.com" xmlns:xs="http://www.w3.org/2001/XMLSchema" version="2.0">
    <xsl:output method="xml" encoding="utf-8" indent="yes"/>
    <xsl:strip-space elements="*"/>
    <xsl:include href="../../../../../Ressources-diverses/xml-xsl/browse.lib.xsl"/>
    <!-- DOCUMENT PRODUCER -->
    <xsl:template match="/">
        <compositionXMLData applies-to="document-generation" version="2">
        
						
			<xsl:copy-of select="/report/graphane-header"/>
        
        
            <xsl:variable name="req" select="report/requests/request"/>
            
            <No.facture>
                <xsl:value-of select="g:browse($req, 'number')"/>
            </No.facture>
            
            <date.facture>
                <xsl:value-of select="g:browse($req, 'date_invoice')"/>
            </date.facture>
            <nom.société>
                <xsl:value-of select="g:browse($req, 'partner.name')"/>
            </nom.société>
            <adresse1.société>
                <xsl:value-of select="g:browse($req, 'address_invoice.street')"/>
            </adresse1.société>
            <adresse3.société><xsl:value-of select="g:browse($req, 'address_invoice.zip')"/></adresse3.société>
            <adresse4.société><xsl:value-of select="g:browse($req, 'address_invoice.city')"/></adresse4.société>
            
            <xsl:variable name="échéances.facture">
                <xsl:for-each select="g:browse($req, 'payment_term.lines')">
                    <xsl:sort select="g:browse(., 'sequence')"/>
                    <échéance.facture>
                        <name><xsl:value-of select="g:browse(., 'name')"/></name>
                        <value-amount><xsl:value-of select="g:browse(., 'value_amount')"/></value-amount>
                        <days><xsl:value-of select="g:browse(., 'days')"/></days>
                        <days2><xsl:value-of select="g:browse(., 'days2')"/></days2>
                        <exemple><xsl:value-of select="g:browse(., 'payment.name')"/></exemple>
                    </échéance.facture>
                </xsl:for-each>
            </xsl:variable>
            
            <échéance.facture><xsl:value-of select="$échéances.facture/échéance.facture[1]/name"/></échéance.facture>
            <No.commande>absent</No.commande>
   			<id.vendeur>absent</id.vendeur>
   			
   			<xsl:variable name="currency" select="g:browse($req, 'currency.symbol')"/>
   			<xsl:variable name="currency-before" select="if ( $currency = '$' ) then '$' else '' "/>
   			<xsl:variable name="currency-after" select="if ( not($currency = '$') ) then $currency else '' "/>
   			
   			<footer1><xsl:value-of select="g:browse($req, 'company.rml_footer1')"/></footer1>
   			<footer2><xsl:value-of select="g:browse($req, 'company.rml_footer2')"/></footer2>
            
            
			<blocks>
				<block name="détail">
						<détail struct="table">
							<xsl:for-each select="g:browse($req, 'invoice_lines')"> 
								<ligne-détail struct="row">
									<quantité><xsl:value-of select="g:browse(., 'quantity')"/></quantité>
									<description><xsl:value-of select="g:browse(., 'name')"/></description>
									<prix>
										<xsl:value-of select="$currency-before"/>
										<xsl:value-of select="g:browse(., 'price_unit')"/>
										<xsl:value-of select="$currency-after"/>
									</prix>
									<montant>
										<xsl:value-of select="$currency-before"/>
										<xsl:value-of select="g:browse(., 'price_subtotal')"/>
										<xsl:value-of select="$currency-after"/>
									</montant>
								</ligne-détail>
							</xsl:for-each>
						</détail>
				</block>
				
				<block name="total">
				
					<sous-total>
						<xsl:value-of select="$currency-before"/>
						<xsl:value-of select="g:browse($req, 'amount_untaxed')"/>
						<xsl:value-of select="$currency-after"/>
					</sous-total>
					
					<tva>
						<xsl:value-of select="$currency-before"/>
						<xsl:value-of select="g:browse($req, 'amount_tax')"/>
						<xsl:value-of select="$currency-after"/>
					</tva>
					
					<total>
						<xsl:value-of select="$currency-before"/>
						<xsl:value-of select="g:browse($req, 'amount_total')"/>
						<xsl:value-of select="$currency-after"/>
					</total>
					
					<avoir>0</avoir>
					
					<montant-dû>
						<xsl:value-of select="$currency-before"/>
						<xsl:value-of select="g:browse($req, 'amount_total')"/>
						<xsl:value-of select="$currency-after"/>
					</montant-dû>
				</block>
				
			</blocks>
							
								
        </compositionXMLData>
    </xsl:template>
</xsl:stylesheet>
