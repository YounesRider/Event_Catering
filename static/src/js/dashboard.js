/** @odoo-module **/

import { Component, onWillStart, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";


class EventCateringDashboard extends Component {


    setup() {

        this.orm = useService("orm");

        this.charts = {};


        onWillStart(async () => {


            if (!window.Chart) {

                await loadJS(
                    "https://cdn.jsdelivr.net/npm/chart.js"
                );

            }


            this.data = await this.orm.call(
                "event.catering.dashboard",
                "get_dashboard_data",
                []
            );


        });



        onMounted(() => {

            this.renderCharts();

        });


    }



    createChart(id, config) {


        const canvas = document.getElementById(id);


        if (!canvas) {
            return;
        }


        // éviter doublons
        if (this.charts[id]) {

            this.charts[id].destroy();

        }


        this.charts[id] = new Chart(
            canvas,
            config
        );

    }





    renderCharts() {


        if (!this.data) {

            console.error(
                "Aucune donnée dashboard"
            );

            return;

        }



        /*
            1 - Etats des événements
        */

        this.createChart(
            "stateChart",
            {

                type: "doughnut",

                data: {

                    labels:
                        this.data.states.labels,


                    datasets: [

                        {

                            label:
                                "États des événements",


                            data:
                                this.data.states.values,

                        }

                    ]

                }

            }
        );





        /*
            2 - Types événements
        */

        this.createChart(
            "typeChart",
            {

                type: "bar",

                data: {

                    labels:
                        this.data.types.labels,


                    datasets: [

                        {

                            label:
                                "Nombre d'événements",


                            data:
                                this.data.types.values,

                        }

                    ]

                }

            }
        );






        /*
            3 - Evolution mensuelle
        */

        this.createChart(
            "monthChart",
            {

                type: "line",

                data: {

                    labels:
                        this.data.months.labels,


                    datasets: [

                        {

                            label:
                                "Événements par mois",


                            data:
                                this.data.months.values,

                        }

                    ]

                }

            }
        );







        /*
            4 - Budget estimé vs réel
        */

        this.createChart(
            "budgetChart",
            {

                type: "bar",


                data: {


                    labels:
                        this.data.budget.labels,


                    datasets: [

                        {

                            label:
                                "Budget estimé",


                            data:
                                this.data.budget.estimated,

                        },


                        {

                            label:
                                "Budget réel",


                            data:
                                this.data.budget.actual,

                        }


                    ]

                }

            }
        );








        /*
            5 - Nombre invités par type
        */

        this.createChart(
            "guestChart",
            {


                type: "bar",


                data: {


                    labels:
                        this.data.guests.labels,


                    datasets: [

                        {

                            label:
                                "Nombre d'invités",


                            data:
                                this.data.guests.values,

                        }

                    ]

                }


            }
        );



    }


}





EventCateringDashboard.template =
    "event_catering_dashboard";



registry
    .category("actions")
    .add(
        "event_catering_dashboard",
        EventCateringDashboard
    );