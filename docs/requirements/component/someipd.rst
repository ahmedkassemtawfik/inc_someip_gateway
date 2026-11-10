..
   # *******************************************************************************
   # Copyright (c) 2026 Contributors to the Eclipse Foundation
   #
   # See the NOTICE file(s) distributed with this work for additional
   # information regarding copyright ownership.
   #
   # This program and the accompanying materials are made available under the
   # terms of the Apache License Version 2.0 which is available at
   # https://www.apache.org/licenses/LICENSE-2.0
   #
   # SPDX-License-Identifier: Apache-2.0
   # *******************************************************************************

someipd Component Requirements
==============================

These requirements cover externally observable SOME/IP daemon behavior. Wire-level
protocol conformance is verified separately, see :doc:`/tc8_conformance/requirements`.

.. comp_req:: someipd offers a local service only while it is available
   :id: comp_req__someipd__offer_follows_availability
   :status: valid
   :version: 1
   :safety: QM
   :security: NO
   :reqtype: Functional
   :derived_from: feat_req__some_ip_gateway__someip_sd_protocol
   :satisfied_by: comp__someipd

   For each configured local service instance, someipd shall send SOME/IP-SD
   OfferService entries only while the bridged service of that instance is
   available from gatewayd. When the bridged service becomes unavailable,
   because its provider stopped offering it or its gatewayd stopped, someipd
   shall send a StopOfferService entry and stop offering the instance. When the
   bridged service becomes available again, someipd shall offer the instance
   again.

   The termination of a provider or of gatewayd is detected only as far as
   ``mw::com`` reports it (see the ``mw::com`` Assumption of Use
   ``NoNotificationOnTerminationOfProducer``): a crashed process is in general
   not detected.
